/* Process-local workaround for duplicate fourccs in Samsung's downstream DRM.
 * Preserve the kernel's allocation and ordering, removing only repeated values.
 * This does not change the kernel, firmware, or any on-device partition.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

/* Weston 13's desktop-shell move handler searches seat->tablet_tool_list,
 * but its input backend puts non-unique tools on tablet->tool_list instead.
 * This integrated S Pen has no MSC_SERIAL. For the compositor's ownership
 * decision only, place this single built-in tool on the seat-level list.
 * Do not alter libinput's own internal decisions or other applications.
 */
struct libinput_tablet_tool;
int libinput_tablet_tool_is_unique(struct libinput_tablet_tool *tool)
{
    static int (*real_is_unique)(struct libinput_tablet_tool *);
    static int reported;
    if (!real_is_unique)
        real_is_unique = dlsym(RTLD_NEXT, "libinput_tablet_tool_is_unique");
    if (!real_is_unique)
        return 0;
    int unique = real_is_unique(tool);
    Dl_info caller;
    if (!unique && dladdr(__builtin_return_address(0), &caller) &&
        caller.dli_fname && strstr(caller.dli_fname, "libweston-13")) {
        if (!reported++)
            fprintf(stderr, "t630-input: enabling Weston 13 drag lookup for the built-in non-unique pen\n");
        return 1;
    }
    return unique;
}

/* Downstream page-flip events carry zero timestamps. That leaves Weston's
 * startup fade permanently black. Supply receipt-time CLOCK_MONOTONIC only
 * for invalid zero timestamps, preserving valid hardware timestamps.
 */
static _Thread_local drmEventContextPtr active_context;

static void repair_timestamp(unsigned int *sec, unsigned int *usec)
{
    static int reported;
    if (*sec == 0 && *usec == 0) {
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC, &ts);
        *sec = ts.tv_sec;
        *usec = ts.tv_nsec / 1000;
        if (!reported++)
            fprintf(stderr, "t630-drm: repaired zero page-flip timestamp\n");
    }
}

static void page_flip(int fd, unsigned int seq, unsigned int sec,
                      unsigned int usec, void *data)
{
    repair_timestamp(&sec, &usec);
    active_context->page_flip_handler(fd, seq, sec, usec, data);
}

static void page_flip2(int fd, unsigned int seq, unsigned int sec,
                       unsigned int usec, unsigned int crtc, void *data)
{
    repair_timestamp(&sec, &usec);
    active_context->page_flip_handler2(fd, seq, sec, usec, crtc, data);
}

int drmHandleEvent(int fd, drmEventContextPtr context)
{
    static int (*real_handle_event)(int, drmEventContextPtr);
    if (!real_handle_event)
        real_handle_event = dlsym(RTLD_NEXT, "drmHandleEvent");
    if (!real_handle_event)
        return -1;
    drmEventContext copy = *context;
    drmEventContextPtr saved = active_context;
    active_context = context;
    if (copy.version >= 2 && copy.page_flip_handler)
        copy.page_flip_handler = page_flip;
    if (copy.version >= 3 && copy.page_flip_handler2)
        copy.page_flip_handler2 = page_flip2;
    int result = real_handle_event(fd, &copy);
    active_context = saved;
    return result;
}

/* This device advertises four interchangeable CRTCs, but its internal DSI
 * panel was physically proven on the first CRTC (113), not the last (186).
 * Preserve resource allocation for drmModeFreeResources; limit enumeration.
 */
drmModeResPtr drmModeGetResources(int fd)
{
    static drmModeResPtr (*real_get_resources)(int);
    if (!real_get_resources)
        real_get_resources = dlsym(RTLD_NEXT, "drmModeGetResources");
    if (!real_get_resources)
        return NULL;
    drmModeResPtr r = real_get_resources(fd);
    if (r && r->count_crtcs > 1 && r->crtcs[0] == 113) {
        fprintf(stderr, "t630-drm: selecting physically verified CRTC %u\n", r->crtcs[0]);
        r->count_crtcs = 1;
    }
    return r;
}

drmModePlanePtr drmModeGetPlane(int fd, uint32_t plane_id)
{
    static drmModePlanePtr (*real_get_plane)(int, uint32_t);
    if (!real_get_plane)
        real_get_plane = dlsym(RTLD_NEXT, "drmModeGetPlane");
    if (!real_get_plane)
        return NULL;
    drmModePlanePtr p = real_get_plane(fd, plane_id);
    if (!p)
        return NULL;
    uint32_t original = p->count_formats;
    uint32_t kept = 0;
    for (uint32_t i = 0; i < original; i++) {
        uint32_t j = 0;
        while (j < kept && p->formats[j] != p->formats[i])
            j++;
        if (j == kept)
            p->formats[kept++] = p->formats[i];
    }
    p->count_formats = kept;
    if (kept != original)
        fprintf(stderr, "t630-drm: plane %u: %u unique formats (%u duplicates removed)\n",
                plane_id, kept, original-kept);
    return p;
}
