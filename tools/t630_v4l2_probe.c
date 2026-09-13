/* Process-local compatibility adapter for the SM-T630 stock decoder.
 * Samsung's msm_vidc node lacks TRY_FMT and only accepts Qualcomm's
 * ION-backed V4L2_MEMORY_USERPTR convention. Never preload this globally.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/ioctl.h>
#include <linux/videodev2.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <unistd.h>

#define MAX_DECODER_FDS 8
#define MAX_V4L2_BUFFERS 32
#define ION_SYSTEM_HEAP_ID 25
#define ION_FLAG_CACHED 1U

struct ion_allocation_data {
    uint64_t len;
    uint32_t heap_id_mask;
    uint32_t flags;
    uint32_t fd;
    uint32_t unused;
};

#define ION_IOC_MAGIC 'I'
#define ION_IOC_ALLOC _IOWR(ION_IOC_MAGIC, 0, struct ion_allocation_data)

struct plane_state {
    int ion_fd;
    void *address;
    size_t length;
    off_t fake_offset;
};

struct buffer_state {
    unsigned int num_planes;
    struct plane_state planes[VIDEO_MAX_PLANES];
};

struct queue_state {
    int active;
    unsigned int count;
    struct buffer_state buffers[MAX_V4L2_BUFFERS];
};

struct decoder_state {
    int fd;
    struct queue_state output;
    struct queue_state capture;
};

static struct decoder_state decoders[MAX_DECODER_FDS];
static pthread_mutex_t state_lock = PTHREAD_MUTEX_INITIALIZER;
static int (*next_ioctl)(int, unsigned long, ...);
static void *(*next_mmap)(void *, size_t, int, int, int, off_t);
static int (*next_munmap)(void *, size_t);
static int (*next_close)(int);

static void resolve_symbols(void)
{
    if (!next_ioctl)
        next_ioctl = dlsym(RTLD_NEXT, "ioctl");
    if (!next_mmap)
        next_mmap = dlsym(RTLD_NEXT, "mmap");
    if (!next_munmap)
        next_munmap = dlsym(RTLD_NEXT, "munmap");
    if (!next_close)
        next_close = dlsym(RTLD_NEXT, "close");
}

static int exact_decoder(int fd)
{
    struct v4l2_capability caps = {0};
    return next_ioctl(fd, VIDIOC_QUERYCAP, &caps) == 0 &&
           strcmp((const char *)caps.driver, "msm_vidc_driver") == 0 &&
           strcmp((const char *)caps.card, "msm_vidc_vdec") == 0;
}

static struct decoder_state *find_decoder(int fd, int create)
{
    struct decoder_state *empty = NULL;
    for (unsigned int i = 0; i < MAX_DECODER_FDS; i++) {
        if (decoders[i].fd == fd)
            return &decoders[i];
        if (decoders[i].fd == -1 && !empty)
            empty = &decoders[i];
    }
    if (!create || !empty || !exact_decoder(fd))
        return NULL;
    memset(empty, 0, sizeof(*empty));
    empty->fd = fd;
    for (unsigned int q = 0; q < 2; q++) {
        struct queue_state *queue = q ? &empty->capture : &empty->output;
        for (unsigned int b = 0; b < MAX_V4L2_BUFFERS; b++)
            for (unsigned int p = 0; p < VIDEO_MAX_PLANES; p++)
                queue->buffers[b].planes[p].ion_fd = -1;
    }
    return empty;
}

static struct queue_state *find_queue(struct decoder_state *decoder,
                                      enum v4l2_buf_type type)
{
    if (type == V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE)
        return &decoder->output;
    if (type == V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE)
        return &decoder->capture;
    return NULL;
}

static void free_queue(struct queue_state *queue)
{
    for (unsigned int b = 0; b < MAX_V4L2_BUFFERS; b++) {
        for (unsigned int p = 0; p < VIDEO_MAX_PLANES; p++) {
            struct plane_state *plane = &queue->buffers[b].planes[p];
            if (plane->address && plane->address != MAP_FAILED)
                next_munmap(plane->address, plane->length);
            if (plane->ion_fd >= 0)
                next_close(plane->ion_fd);
            plane->ion_fd = -1;
            plane->address = NULL;
            plane->length = 0;
        }
        queue->buffers[b].num_planes = 0;
    }
    queue->active = 0;
    queue->count = 0;
}

static int allocate_ion(size_t length)
{
    struct ion_allocation_data allocation = {
        .len = length,
        .heap_id_mask = 1U << ION_SYSTEM_HEAP_ID,
        .flags = ION_FLAG_CACHED,
    };
    int ion = open("/dev/ion", O_RDWR | O_CLOEXEC);
    int saved;
    if (ion < 0)
        return -1;
    if (next_ioctl(ion, ION_IOC_ALLOC, &allocation) < 0) {
        saved = errno;
        next_close(ion);
        errno = saved;
        return -1;
    }
    next_close(ion);
    return (int)allocation.fd;
}

static int emulate_querybuf(int fd, struct v4l2_buffer *buffer,
                            struct decoder_state *decoder)
{
    struct queue_state *queue = find_queue(decoder, buffer->type);
    struct v4l2_format format = {.type = buffer->type};
    struct buffer_state *slot;
    unsigned int num_planes;
    if (!queue || !queue->active || buffer->memory != V4L2_MEMORY_MMAP ||
        buffer->index >= queue->count || buffer->index >= MAX_V4L2_BUFFERS ||
        next_ioctl(fd, VIDIOC_G_FMT, &format) < 0)
        return -1;
    num_planes = format.fmt.pix_mp.num_planes;
    if (!num_planes || num_planes > VIDEO_MAX_PLANES) {
        errno = EINVAL;
        return -1;
    }
    slot = &queue->buffers[buffer->index];
    slot->num_planes = num_planes;
    buffer->length = num_planes;
    buffer->memory = V4L2_MEMORY_MMAP;
    for (unsigned int p = 0; p < num_planes; p++) {
        struct plane_state *plane = &slot->planes[p];
        size_t length = format.fmt.pix_mp.plane_fmt[p].sizeimage;
        if (!length) {
            errno = EINVAL;
            return -1;
        }
        if (plane->ion_fd < 0) {
            plane->ion_fd = allocate_ion(length);
            if (plane->ion_fd < 0)
                return -1;
            plane->length = length;
            plane->fake_offset =
                (buffer->type == V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE ?
                 0x10000000LL : 0x20000000LL) +
                (off_t)(buffer->index * VIDEO_MAX_PLANES + p + 1) * 4096;
            if (buffer->type == V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE && p > 0) {
                plane->address = next_mmap(NULL, length,
                                           PROT_READ | PROT_WRITE, MAP_SHARED,
                                           plane->ion_fd, 0);
                if (plane->address == MAP_FAILED)
                    return -1;
            }
        }
        /* Qualcomm appends an extradata plane to linear NV12. FFmpeg's
         * generic V4L2 code would mistake it for the chroma plane. Keep it
         * registered with the driver but expose only the contiguous image. */
        buffer->m.planes[p].length =
            buffer->type == V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE && p > 0 ?
            0 : length;
        buffer->m.planes[p].m.mem_offset = plane->fake_offset;
        buffer->m.planes[p].data_offset = 0;
    }
    return 0;
}

static int translate_qbuf(int fd, struct v4l2_buffer *original,
                          struct decoder_state *decoder)
{
    struct queue_state *queue = find_queue(decoder, original->type);
    struct v4l2_buffer translated = *original;
    struct v4l2_plane planes[VIDEO_MAX_PLANES];
    struct buffer_state *slot;
    if (!queue || original->index >= queue->count ||
        original->index >= MAX_V4L2_BUFFERS) {
        errno = EINVAL;
        return -1;
    }
    slot = &queue->buffers[original->index];
    if (!slot->num_planes || !original->length) {
        errno = EINVAL;
        return -1;
    }
    memcpy(planes, original->m.planes, sizeof(planes));
    translated.memory = V4L2_MEMORY_USERPTR;
    translated.length = slot->num_planes;
    translated.m.planes = planes;
    for (unsigned int p = 0; p < slot->num_planes; p++) {
        struct plane_state *plane = &slot->planes[p];
        if (!plane->address || plane->address == MAP_FAILED || plane->ion_fd < 0) {
            errno = EINVAL;
            return -1;
        }
        planes[p].length = plane->length;
        planes[p].m.userptr = (uintptr_t)plane->address;
        planes[p].reserved[0] = plane->ion_fd;
        planes[p].reserved[1] = 0;
    }
    return next_ioctl(fd, VIDIOC_QBUF, &translated);
}

static int translate_dqbuf(int fd, struct v4l2_buffer *original,
                           struct decoder_state *decoder)
{
    struct queue_state *queue = find_queue(decoder, original->type);
    struct v4l2_buffer translated = *original;
    struct v4l2_plane planes[VIDEO_MAX_PLANES] = {{0}};
    struct v4l2_plane *original_planes = original->m.planes;
    int result;
    if (!queue) {
        errno = EINVAL;
        return -1;
    }
    translated.memory = V4L2_MEMORY_USERPTR;
    translated.m.planes = planes;
    translated.length = queue->buffers[0].num_planes;
    if (!translated.length) {
        errno = EINVAL;
        return -1;
    }
    result = next_ioctl(fd, VIDIOC_DQBUF, &translated);
    if (result < 0)
        return result;
    if (getenv("T630_V4L2_DEBUG"))
        dprintf(STDERR_FILENO,
                "t630-v4l2: dq type=%u index=%u flags=0x%x planes=%u bytes=%u/%u\n",
                translated.type, translated.index, translated.flags,
                translated.length, planes[0].bytesused, planes[1].bytesused);
    if (translated.index >= queue->count ||
        translated.index >= MAX_V4L2_BUFFERS) {
        errno = EIO;
        return -1;
    }
    if (translated.type == V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE &&
        planes[0].bytesused) {
        struct v4l2_format format = {.type = translated.type};
        struct plane_state *image = &queue->buffers[translated.index].planes[0];

        if (next_ioctl(fd, VIDIOC_G_FMT, &format) == 0 &&
            format.fmt.pix_mp.pixelformat == V4L2_PIX_FMT_NV12) {
            size_t stride = format.fmt.pix_mp.plane_fmt[0].bytesperline;
            size_t height = format.fmt.pix_mp.height;
            size_t y_scanlines = (height + 511U) & ~511U;
            size_t source_offset = stride * y_scanlines;
            size_t target_offset = stride * height;
            size_t chroma_size = stride * ((height + 1U) / 2U);

            if (image->address && source_offset + chroma_size <= image->length &&
                target_offset + chroma_size <= image->length)
                memmove((char *)image->address + target_offset,
                        (char *)image->address + source_offset, chroma_size);
        }
    }
    *original = translated;
    original->memory = V4L2_MEMORY_MMAP;
    original->m.planes = original_planes;
    memcpy(original_planes, planes, sizeof(planes));
    for (unsigned int p = 0; p < original->length; p++)
        original_planes[p].m.mem_offset =
            queue->buffers[original->index].planes[p].fake_offset;
    return 0;
}

__attribute__((constructor)) static void initialize_state(void)
{
    for (unsigned int i = 0; i < MAX_DECODER_FDS; i++)
        decoders[i].fd = -1;
}

int ioctl(int fd, unsigned long request, ...)
{
    va_list args;
    void *arg;
    int result;
    int saved;
    struct decoder_state *decoder;
    resolve_symbols();
    va_start(args, request);
    arg = va_arg(args, void *);
    va_end(args);
    pthread_mutex_lock(&state_lock);
    decoder = find_decoder(fd, request == VIDIOC_TRY_FMT ||
                               request == VIDIOC_REQBUFS);
    if (decoder && request == VIDIOC_REQBUFS) {
        struct v4l2_requestbuffers *original = arg;
        struct v4l2_requestbuffers translated = *original;
        struct queue_state *queue = find_queue(decoder, original->type);
        if (queue && original->memory == V4L2_MEMORY_MMAP) {
            translated.memory = V4L2_MEMORY_USERPTR;
            result = next_ioctl(fd, request, &translated);
            saved = errno;
            if (result == 0) {
                if (!original->count)
                    free_queue(queue);
                else {
                    queue->active = 1;
                    queue->count = translated.count > MAX_V4L2_BUFFERS ?
                                   MAX_V4L2_BUFFERS : translated.count;
                }
                original->count = queue->count;
            }
            pthread_mutex_unlock(&state_lock);
            errno = saved;
            return result;
        }
    }
    if (decoder && request == VIDIOC_QUERYBUF) {
        result = emulate_querybuf(fd, arg, decoder);
        saved = errno;
        pthread_mutex_unlock(&state_lock);
        errno = saved;
        return result;
    }
    if (decoder && request == VIDIOC_QBUF) {
        result = translate_qbuf(fd, arg, decoder);
        saved = errno;
        pthread_mutex_unlock(&state_lock);
        errno = saved;
        return result;
    }
    if (decoder && request == VIDIOC_DQBUF) {
        result = translate_dqbuf(fd, arg, decoder);
        saved = errno;
        pthread_mutex_unlock(&state_lock);
        errno = saved;
        return result;
    }
    pthread_mutex_unlock(&state_lock);
    result = next_ioctl(fd, request, arg);
    if (result == -1 && errno == ENOTTY && request == VIDIOC_TRY_FMT) {
        struct v4l2_capability caps = {0};
        saved = errno;
        if (next_ioctl(fd, VIDIOC_QUERYCAP, &caps) == 0 &&
            strcmp((const char *)caps.driver, "msm_vidc_driver") == 0 &&
            strcmp((const char *)caps.card, "msm_vidc_vdec") == 0) {
            struct v4l2_format *format = arg;
            if (format->type == V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE &&
                (!format->fmt.pix_mp.width || !format->fmt.pix_mp.height)) {
                result = next_ioctl(fd, VIDIOC_G_FMT, arg);
                if (result < 0)
                    return result;
                format->fmt.pix_mp.pixelformat = V4L2_PIX_FMT_NV12;
                return next_ioctl(fd, VIDIOC_S_FMT, arg);
            }
            return next_ioctl(fd, VIDIOC_S_FMT, arg);
        }
        errno = saved;
    }
    return result;
}

static void *translated_mmap(void *address, size_t length, int prot, int flags,
                             int fd, off_t offset)
{
    void *result;
    resolve_symbols();
    pthread_mutex_lock(&state_lock);
    for (unsigned int d = 0; d < MAX_DECODER_FDS; d++) {
        if (decoders[d].fd != fd)
            continue;
        for (unsigned int q = 0; q < 2; q++) {
            struct queue_state *queue = q ? &decoders[d].capture :
                                              &decoders[d].output;
            for (unsigned int b = 0; b < queue->count; b++) {
                for (unsigned int p = 0;
                     p < queue->buffers[b].num_planes; p++) {
                    struct plane_state *plane = &queue->buffers[b].planes[p];
                    if (plane->fake_offset != offset)
                        continue;
                    result = next_mmap(address, length, prot, flags,
                                       plane->ion_fd, 0);
                    if (result != MAP_FAILED)
                        plane->address = result;
                    pthread_mutex_unlock(&state_lock);
                    return result;
                }
            }
        }
    }
    pthread_mutex_unlock(&state_lock);
    return next_mmap(address, length, prot, flags, fd, offset);
}

void *mmap(void *address, size_t length, int prot, int flags, int fd,
           off_t offset)
{
    return translated_mmap(address, length, prot, flags, fd, offset);
}

void *mmap64(void *address, size_t length, int prot, int flags, int fd,
             off64_t offset)
{
    return translated_mmap(address, length, prot, flags, fd, (off_t)offset);
}

int munmap(void *address, size_t length)
{
    resolve_symbols();
    pthread_mutex_lock(&state_lock);
    for (unsigned int d = 0; d < MAX_DECODER_FDS; d++) {
        for (unsigned int q = 0; q < 2; q++) {
            struct queue_state *queue = q ? &decoders[d].capture :
                                              &decoders[d].output;
            for (unsigned int b = 0; b < queue->count; b++) {
                for (unsigned int p = 0;
                     p < queue->buffers[b].num_planes; p++) {
                    struct plane_state *plane = &queue->buffers[b].planes[p];
                    if (plane->address == address && plane->length == length)
                        plane->address = NULL;
                }
            }
        }
    }
    pthread_mutex_unlock(&state_lock);
    return next_munmap(address, length);
}

int close(int fd)
{
    resolve_symbols();
    pthread_mutex_lock(&state_lock);
    for (unsigned int d = 0; d < MAX_DECODER_FDS; d++) {
        if (decoders[d].fd == fd) {
            free_queue(&decoders[d].output);
            free_queue(&decoders[d].capture);
            decoders[d].fd = -1;
            break;
        }
    }
    pthread_mutex_unlock(&state_lock);
    return next_close(fd);
}
