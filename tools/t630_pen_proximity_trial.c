/* Manual, unaccepted Mutter 46.2 nested-X11 proximity bridge prototype.
 * Not packaged or loaded by default. Existing physical tablet events are
 * forwarded unchanged; tool lifecycle reconstruction was attempted but did
 * not produce accepted pen delivery. Retained only to reproduce the failure.
 * No evdev access, coordinate logging, pressure scaling, grabs or strokes.
 * ABI: GNOME/mutter tag 46.2 clutter-event-private.h. Requires a separately
 * verified exact libmutter/Clutter build before loading into a lab session.
 * Known limitation: physical hover-out is not yet available in XI2; switching
 * to another pointer or touch closes proximity. This is NOT release-ready.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef struct { float x, y; } Point;
typedef void *(*Motion)(int, int64_t, void *, void *, int,
                       Point, Point, Point, Point, double *);
typedef void *(*Touch)(int, int, int64_t, void *, void *, int, Point);
typedef void *(*Proximity)(int, int, int64_t, void *, void *);
static Motion next_motion;
static Touch next_touch;
static Proximity proximity;
static const char *(*device_name)(void *);
static uint64_t (*tool_serial)(void *);
static void (*put_event)(const void *);
static void (*free_event)(void *);
static void *(*object_ref)(void *);
static void (*object_unref)(void *);
static void *active_device, *active_tool;
static int initialized, enabled;
static int reported_pen;
static void *(*next_object_new)(uintptr_t, const char *, ...);
static void *(*next_object_valist)(uintptr_t, const char *, va_list);
static const char *(*type_name)(uintptr_t);

static void initialize(void)
{
    if (initialized) return;
    initialized = 1;
    next_motion = (Motion)dlsym(RTLD_NEXT, "clutter_event_motion_new");
    next_touch = (Touch)dlsym(RTLD_NEXT, "clutter_event_touch_new");
    proximity = (Proximity)dlsym(RTLD_NEXT, "clutter_event_proximity_new");
    device_name = dlsym(RTLD_DEFAULT, "clutter_input_device_get_device_name");
    tool_serial = dlsym(RTLD_DEFAULT, "clutter_input_device_tool_get_serial");
    put_event = dlsym(RTLD_DEFAULT, "clutter_event_put");
    free_event = dlsym(RTLD_DEFAULT, "clutter_event_free");
    object_ref = dlsym(RTLD_DEFAULT, "g_object_ref");
    object_unref = dlsym(RTLD_DEFAULT, "g_object_unref");
    next_object_new = dlsym(RTLD_NEXT, "g_object_new");
    next_object_valist = dlsym(RTLD_NEXT, "g_object_new_valist");
    type_name = dlsym(RTLD_DEFAULT, "g_type_name");
    const char *trial = getenv("T630_PEN_PROXIMITY_TRIAL");
    const char *display = getenv("DISPLAY");
    enabled = geteuid() != 0 && trial && !strcmp(trial, "1") &&
        display && !strcmp(display, ":3") && proximity && device_name &&
        tool_serial && put_event && free_event && object_ref && object_unref;
    fprintf(stderr, "T630 pen proximity trial initialized: enabled=%d\n", enabled);
}

__attribute__((constructor)) static void audit_load(void)
{
    initialize();
}

static int private_pen(void *device, void *tool)
{
    if (!device || !tool || tool_serial(tool) != 630) return 0;
    const char *name = device_name(device), *suffix = NULL;
    const char *prefixes[] = {"xwayland-tablet stylus:", "xwayland-tablet eraser:"};
    if (!name) return 0;
    for (unsigned i = 0; i < 2; i++) {
        size_t length = strlen(prefixes[i]);
        if (!strncmp(name, prefixes[i], length)) suffix = name + length;
    }
    if (!suffix || !*suffix) return 0;
    for (; *suffix; suffix++) if (*suffix < '0' || *suffix > '9') return 0;
    return 1;
}

/* Match the exact 46.2 MetaInputDeviceX11 constructor, otherwise forward the
 * untouched original va_list. A pen's floating mode is construct-only and
 * must precede input-device enumeration, just like its Wacom tool identity.
 */
void *g_object_new(uintptr_t type, const char *first, ...)
{
    initialize();
    if (!next_object_valist) abort();
    va_list args, copy;
    va_start(args, first);
    if (enabled && next_object_new && type_name && type_name(type) &&
        !strcmp(type_name(type), "MetaInputDeviceX11")) {
        const char *property = first;
        void *backend, *seat;
        const char *name, *vendor, *product, *node;
        int id, cursor, source, mode;
        unsigned capabilities, rings, strips, groups;
        va_copy(copy, args);
#define READ_PROPERTY(key, ctype, variable) do { \
    if (!property || strcmp(property, key)) goto unchanged; \
    variable = va_arg(copy, ctype); property = va_arg(copy, const char *); \
} while (0)
        READ_PROPERTY("backend", void *, backend);
        READ_PROPERTY("name", const char *, name);
        READ_PROPERTY("id", int, id);
        READ_PROPERTY("has-cursor", int, cursor);
        READ_PROPERTY("device-type", int, source);
        READ_PROPERTY("capabilities", unsigned, capabilities);
        READ_PROPERTY("device-mode", int, mode);
        READ_PROPERTY("vendor-id", const char *, vendor);
        READ_PROPERTY("product-id", const char *, product);
        READ_PROPERTY("device-node", const char *, node);
        READ_PROPERTY("n-rings", unsigned, rings);
        READ_PROPERTY("n-strips", unsigned, strips);
        READ_PROPERTY("n-mode-groups", unsigned, groups);
        READ_PROPERTY("seat", void *, seat);
#undef READ_PROPERTY
        if (!property && mode == 1 && name &&
            (!strncmp(name, "xwayland-tablet stylus:", sizeof("xwayland-tablet stylus:") - 1) ||
             !strncmp(name, "xwayland-tablet eraser:", sizeof("xwayland-tablet eraser:") - 1))) {
            const char *digits = name + sizeof("xwayland-tablet stylus:") - 1;
            if (!*digits) goto unchanged;
            for (; *digits; digits++) if (*digits < '0' || *digits > '9') goto unchanged;
            va_end(copy); va_end(args);
            fprintf(stderr, "T630 pen proximity trial: independent tablet device constructed\n");
            return next_object_new(type, "backend", backend, "name", name,
                "id", id, "has-cursor", cursor, "device-type", source,
                "capabilities", capabilities, "device-mode", 2,
                "vendor-id", vendor, "product-id", product, "device-node", node,
                "n-rings", rings, "n-strips", strips, "n-mode-groups", groups,
                "seat", seat, NULL);
        }
unchanged:
        va_end(copy);
    }
    void *object = next_object_valist(type, first, args);
    va_end(args);
    return object;
}

static void close_tool(int64_t timestamp)
{
    if (!active_device) return;
    /* Actual Clutter 46.2 enum values, verified from the installed typelib. */
    void *event = proximity(17, 1, timestamp, active_device, active_tool);
    if (event) { put_event(event); free_event(event); }
    object_unref(active_tool);
    object_unref(active_device);
    active_device = active_tool = NULL;
}

void *clutter_event_motion_new(int flags, int64_t timestamp, void *device,
    void *tool, int modifiers, Point coords, Point delta,
    Point unaccelerated, Point constrained, double *axes)
{
    initialize();
    if (!next_motion) abort();
    if (enabled) {
        if (!reported_pen && device && device_name(device) &&
            strstr(device_name(device), "xwayland-tablet stylus:") == device_name(device)) {
            reported_pen = 1;
            fprintf(stderr, "T630 pen proximity trial stylus motion: tool_present=%d serial=%llu\n",
                    tool != NULL, (unsigned long long)(tool ? tool_serial(tool) : 0));
        }
        if (!private_pen(device, tool)) close_tool(timestamp);
        else if (active_device != device || active_tool != tool) {
            close_tool(timestamp);
            void *event = proximity(16, 1, timestamp, device, tool);
            if (event) {
                active_device = object_ref(device);
                active_tool = object_ref(tool);
                put_event(event);
                free_event(event);
            }
        }
    }
    return next_motion(flags, timestamp, device, tool, modifiers, coords,
                       delta, unaccelerated, constrained, axes);
}

void *clutter_event_touch_new(int type, int flags, int64_t timestamp,
    void *device, void *sequence, int modifiers, Point coords)
{
    initialize();
    if (!next_touch) abort();
    if (enabled) close_tool(timestamp);
    return next_touch(type, flags, timestamp, device, sequence, modifiers, coords);
}
