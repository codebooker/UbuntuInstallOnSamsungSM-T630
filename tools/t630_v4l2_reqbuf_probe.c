#include <errno.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static int xioctl(int fd, unsigned long request, void *arg)
{
    int rc;
    do {
        rc = ioctl(fd, request, arg);
    } while (rc < 0 && errno == EINTR);
    return rc;
}

static int configure(int fd)
{
    struct v4l2_capability cap = {0};
    struct v4l2_format out = {0};
    struct v4l2_format capture = {0};

    if (xioctl(fd, VIDIOC_QUERYCAP, &cap) < 0) {
        perror("VIDIOC_QUERYCAP");
        return -1;
    }
    if (strcmp((const char *)cap.driver, "msm_vidc_driver") != 0 ||
        strcmp((const char *)cap.card, "msm_vidc_vdec") != 0) {
        fprintf(stderr, "refusing unexpected device: driver=%s card=%s\n",
                cap.driver, cap.card);
        return -1;
    }

    out.type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    out.fmt.pix_mp.width = 320;
    out.fmt.pix_mp.height = 240;
    out.fmt.pix_mp.pixelformat = V4L2_PIX_FMT_H264;
    out.fmt.pix_mp.field = V4L2_FIELD_ANY;
    out.fmt.pix_mp.num_planes = 1;
    if (xioctl(fd, VIDIOC_S_FMT, &out) < 0) {
        perror("VIDIOC_S_FMT(output)");
        return -1;
    }

    capture.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    capture.fmt.pix_mp.width = 320;
    capture.fmt.pix_mp.height = 240;
    capture.fmt.pix_mp.pixelformat = v4l2_fourcc('Q', '1', '2', '8');
    capture.fmt.pix_mp.field = V4L2_FIELD_ANY;
    capture.fmt.pix_mp.num_planes = 2;
    if (xioctl(fd, VIDIOC_S_FMT, &capture) < 0) {
        perror("VIDIOC_S_FMT(capture)");
        return -1;
    }

    return 0;
}

static void probe(enum v4l2_buf_type type, enum v4l2_memory memory,
                  const char *queue_name, const char *memory_name)
{
    int fd = open("/dev/video32", O_RDWR | O_NONBLOCK | O_CLOEXEC);
    struct v4l2_requestbuffers req = {0};

    if (fd < 0) {
        perror("open /dev/video32");
        return;
    }
    if (configure(fd) < 0) {
        close(fd);
        return;
    }

    req.type = type;
    req.memory = memory;
    req.count = 16;
    errno = 0;
    if (xioctl(fd, VIDIOC_REQBUFS, &req) == 0)
        printf("%-7s %-7s accepted count=%u capabilities=0x%x flags=0x%x\n",
               queue_name, memory_name, req.count, req.capabilities, req.flags);
    else
        printf("%-7s %-7s rejected errno=%d (%s)\n",
               queue_name, memory_name, errno, strerror(errno));

    close(fd);
}

static void enumerate_formats(enum v4l2_buf_type type, const char *queue_name)
{
    int fd = open("/dev/video32", O_RDWR | O_NONBLOCK | O_CLOEXEC);
    struct v4l2_fmtdesc format = {.type = type};

    if (fd < 0) {
        perror("open /dev/video32");
        return;
    }
    printf("%s formats:\n", queue_name);
    while (xioctl(fd, VIDIOC_ENUM_FMT, &format) == 0) {
        uint32_t f = format.pixelformat;
        printf("  %2u %c%c%c%c %s\n", format.index,
               f & 0xff, (f >> 8) & 0xff, (f >> 16) & 0xff,
               (f >> 24) & 0xff, format.description);
        format.index++;
    }
    close(fd);
}

int main(void)
{
    const enum v4l2_buf_type queues[] = {
        V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE,
        V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE,
    };
    const char *queue_names[] = {"output", "capture"};
    const enum v4l2_memory memories[] = {
        V4L2_MEMORY_MMAP,
        V4L2_MEMORY_USERPTR,
        V4L2_MEMORY_DMABUF,
    };
    const char *memory_names[] = {"MMAP", "USERPTR", "DMABUF"};

    for (unsigned int q = 0; q < 2; q++) {
        enumerate_formats(queues[q], queue_names[q]);
        for (unsigned int m = 0; m < 3; m++)
            probe(queues[q], memories[m], queue_names[q], memory_names[m]);
    }
    return 0;
}
