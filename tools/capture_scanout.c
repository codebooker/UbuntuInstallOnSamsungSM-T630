/* Read-only capture of the current CRTC buffer. No modesets or pixel writes. */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <drm_fourcc.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

int main(int argc, char **argv) {
    int stream = argc == 2 && strcmp(argv[1], "--stdout") == 0;
    if (argc > 1 && !stream) return 2;
    int fd = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
    if (fd < 0) { perror("open DRM"); return 1; }
    drmModeCrtcPtr crtc = drmModeGetCrtc(fd, 113);
    if (!crtc || !crtc->buffer_id) { fprintf(stderr, "No active CRTC buffer\n"); return 1; }
    drmModeFB2Ptr fb = drmModeGetFB2(fd, crtc->buffer_id);
    if (!fb) {
        drmModeFBPtr legacy = drmModeGetFB(fd, crtc->buffer_id);
        if (!legacy || legacy->bpp != 32 || legacy->depth != 24) {
            perror("GetFB legacy"); return 1;
        }
        fb = calloc(1, sizeof(*fb));
        if (!fb) return 1;
        fb->fb_id = legacy->fb_id;
        fb->width = legacy->width;
        fb->height = legacy->height;
        fb->handles[0] = legacy->handle;
        fb->pitches[0] = legacy->pitch;
        /* Legacy DRM depth=24/bpp=32 framebuffer convention. */
        fb->pixel_format = DRM_FORMAT_XRGB8888;
        if (!stream) fprintf(stderr, "Legacy GetFB: using depth24/bpp32 XRGB convention\n");
        drmModeFreeFB(legacy);
    }
    if (!fb->handles[0]) { fprintf(stderr, "No exported framebuffer handle\n"); return 1; }
    if (!stream) fprintf(stderr, "CRTC %u framebuffer %u size %ux%u fourcc 0x%x pitch %u\n",
           crtc->crtc_id, fb->fb_id, fb->width, fb->height, fb->pixel_format, fb->pitches[0]);
    int bgr;
    switch (fb->pixel_format) {
    case DRM_FORMAT_XRGB8888: case DRM_FORMAT_ARGB8888: bgr = 1; break;
    case DRM_FORMAT_XBGR8888: case DRM_FORMAT_ABGR8888: bgr = 0; break;
    default: fprintf(stderr, "Unsupported scanout format\n"); return 1;
    }
    if (fb->modifier || fb->width > 4096 || fb->height > 4096 ||
        fb->pitches[0] < fb->width * 4 || fb->handles[1]) {
        fprintf(stderr, "Refusing non-linear or unexpected buffer\n"); return 1;
    }
    struct drm_mode_map_dumb map = { .handle = fb->handles[0] };
    if (drmIoctl(fd, DRM_IOCTL_MODE_MAP_DUMB, &map)) { perror("MAP_DUMB"); return 1; }
    size_t size = fb->offsets[0] + (size_t)fb->pitches[0] * fb->height;
    uint8_t *pixels = mmap(NULL, size, PROT_READ, MAP_SHARED, fd, map.offset);
    if (pixels == MAP_FAILED) { perror("mmap read-only"); return 1; }
    FILE *out = stream ? stdout : fopen("/tmp/t630-scanout.ppm", "wbx");
    if (!out) { perror("new output"); return 1; }
    fprintf(out, "P6\n%u %u\n255\n", fb->width, fb->height);
    uint8_t *rgb = malloc(fb->width * 3);
    if (!rgb) return 1;
    for (uint32_t y = 0; y < fb->height; y++) {
        uint8_t *row = pixels + fb->offsets[0] + (size_t)y * fb->pitches[0];
        for (uint32_t x = 0; x < fb->width; x++) {
            rgb[x*3] = row[x*4 + (bgr ? 2 : 0)];
            rgb[x*3+1] = row[x*4+1];
            rgb[x*3+2] = row[x*4 + (bgr ? 0 : 2)];
        }
        if (fwrite(rgb, 3, fb->width, out) != fb->width) { perror("write"); return 1; }
    }
    free(rgb);
    if (fclose(out)) return 1;
    munmap(pixels, size);
    /* Closing our DRM fd releases the temporary GEM handles, not the scanout. */
    drmModeFreeFB2(fb);
    drmModeFreeCrtc(crtc);
    close(fd);
    return 0;
}
