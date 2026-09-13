/* GTK3 -> Weston text-input-v1 bridge. Opt-in per application, no key logging.
 * SPDX-License-Identifier: MIT
 * Hardware keys retain GtkIMContextSimple's normal handling.
 */
#include <gtk/gtk.h>
#include <gtk/gtkimmodule.h>
#include <gdk/gdkwayland.h>
#include <wayland-client.h>
#include <stdint.h>
#include <string.h>
#include "text-input-v1-client.h"

typedef struct {
    GtkIMContextSimple parent;
    GdkWindow *window;
    struct wl_registry *registry;
    struct zwp_text_input_manager_v1 *manager;
    struct zwp_text_input_v1 *input;
    struct wl_seat *seat;
    gboolean focused, active;
    gchar *preedit, *preedit_commit, *surrounding;
    gint preedit_cursor, surrounding_cursor, delete_index;
    guint delete_length;
    uint32_t serial, reset_serial;
    GdkModifierType modifiers[32];
} T630IM;
typedef struct { GtkIMContextSimpleClass parent; } T630IMClass;
G_DEFINE_DYNAMIC_TYPE(T630IM, t630_im, GTK_TYPE_IM_CONTEXT_SIMPLE)

static void update_state(T630IM *im);
static gboolean current(T630IM *im, uint32_t serial) {
    return im->focused && im->active && (int32_t)(serial-im->reset_serial) >= 0;
}
static gboolean private_field(T630IM *im) {
    GtkInputPurpose purpose;
    g_object_get(im, "input-purpose", &purpose, NULL);
    return purpose == GTK_INPUT_PURPOSE_PASSWORD || purpose == GTK_INPUT_PURPOSE_PIN;
}
static void clear_preedit(T630IM *im) {
    gboolean had = im->preedit && *im->preedit;
    g_clear_pointer(&im->preedit, g_free);
    g_clear_pointer(&im->preedit_commit, g_free);
    im->preedit_cursor = 0;
    if (had) {
        g_signal_emit_by_name(im, "preedit-changed");
        g_signal_emit_by_name(im, "preedit-end");
    }
}
static void entered(void *data, struct zwp_text_input_v1 *input, struct wl_surface *surface) {
    (void)surface;
    T630IM *im = data;
    if (!im->focused) return;
    im->active = TRUE;
    update_state(im);
    zwp_text_input_v1_show_input_panel(input);
}
static void left(void *data, struct zwp_text_input_v1 *input) {
    (void)input;
    T630IM *im = data;
    im->active = FALSE;
    clear_preedit(im);
}
static void modifier_map(void *data, struct zwp_text_input_v1 *input, struct wl_array *map) {
    (void)input;
    T630IM *im = data;
    memset(im->modifiers, 0, sizeof(im->modifiers));
    const char *p = map->data, *end = p+map->size;
    for (unsigned i=0; p<end && i<32; i++) {
        size_t length = strnlen(p, (size_t)(end-p));
        if (length == (size_t)(end-p)) break;
        if (!strcmp(p,"Shift")) im->modifiers[i] = GDK_SHIFT_MASK;
        else if (!strcmp(p,"Control")) im->modifiers[i] = GDK_CONTROL_MASK;
        else if (!strcmp(p,"Mod1")) im->modifiers[i] = GDK_MOD1_MASK;
        p += length+1;
    }
}
static void panel_state(void *data, struct zwp_text_input_v1 *input, uint32_t state) {
    (void)data; (void)input; (void)state;
}
static void preedit_string(void *data, struct zwp_text_input_v1 *input, uint32_t serial,
                           const char *text, const char *commit) {
    (void)input;
    T630IM *im = data;
    if (!current(im,serial) || !g_utf8_validate(text,-1,NULL)) return;
    gboolean had = im->preedit && *im->preedit;
    g_free(im->preedit); im->preedit = g_strdup(text);
    g_free(im->preedit_commit); im->preedit_commit = g_strdup(commit);
    if (!had && *text) g_signal_emit_by_name(im,"preedit-start");
    g_signal_emit_by_name(im,"preedit-changed");
    if (had && !*text) g_signal_emit_by_name(im,"preedit-end");
}
static void preedit_style(void *data, struct zwp_text_input_v1 *input, uint32_t index,
                          uint32_t length, uint32_t style) {
    /* A consistent underline is used for this simple keyboard's composition. */
    (void)data; (void)input; (void)index; (void)length; (void)style;
}
static void preedit_cursor(void *data, struct zwp_text_input_v1 *input, int32_t index) {
    (void)input;
    ((T630IM *)data)->preedit_cursor = index;
}
static void commit_string(void *data, struct zwp_text_input_v1 *input, uint32_t serial,
                          const char *text) {
    (void)input;
    T630IM *im = data;
    if (!current(im,serial) || !g_utf8_validate(text,-1,NULL)) return;
    if (im->delete_length && im->surrounding) {
        gint64 start = (gint64)im->surrounding_cursor+im->delete_index;
        gint64 end = start+im->delete_length;
        gsize size = strlen(im->surrounding);
        if (start>=0 && end>=start && end<=(gint64)size &&
            g_utf8_validate(im->surrounding,start,NULL) &&
            g_utf8_validate(im->surrounding+start,end-start,NULL)) {
            gint cursor = g_utf8_pointer_to_offset(im->surrounding,im->surrounding+im->surrounding_cursor);
            gint first = g_utf8_pointer_to_offset(im->surrounding,im->surrounding+start);
            gint count = g_utf8_strlen(im->surrounding+start,end-start);
            gtk_im_context_delete_surrounding(GTK_IM_CONTEXT(im),first-cursor,count);
        }
    }
    im->delete_length = 0;
    clear_preedit(im);
    if (*text) g_signal_emit_by_name(im,"commit",text);
    update_state(im);
}
static void cursor_position(void *data, struct zwp_text_input_v1 *input, int32_t index, int32_t anchor) {
    /* No selection-replacement feature is advertised by this bridge. */
    (void)data; (void)input; (void)index; (void)anchor;
}
static void delete_text(void *data, struct zwp_text_input_v1 *input, int32_t index, uint32_t length) {
    (void)input;
    T630IM *im = data;
    im->delete_index = index; im->delete_length = length;
}
static void keysym(void *data, struct zwp_text_input_v1 *input, uint32_t serial,
                   uint32_t time, uint32_t sym, uint32_t state, uint32_t modifiers) {
    (void)input;
    T630IM *im = data;
    if (!current(im,serial) || !im->window || gdk_window_is_destroyed(im->window)) return;
    GdkEvent *event = gdk_event_new(state ? GDK_KEY_PRESS : GDK_KEY_RELEASE);
    event->key.window = g_object_ref(im->window);
    event->key.send_event = TRUE;
    event->key.time = time;
    event->key.keyval = sym;
    event->key.string = g_strdup("");
    for (unsigned i=0; i<32; i++)
        if (modifiers & (1u<<i)) event->key.state |= im->modifiers[i];
    GdkSeat *seat = gdk_display_get_default_seat(gdk_window_get_display(im->window));
    GdkDevice *keyboard = gdk_seat_get_keyboard(seat);
    if (keyboard) gdk_event_set_device(event,keyboard);
    gdk_event_put(event);
    gdk_event_free(event);
}
static void language(void *data, struct zwp_text_input_v1 *input, uint32_t serial, const char *lang) {
    (void)data; (void)input; (void)serial; (void)lang;
}
static void direction(void *data, struct zwp_text_input_v1 *input, uint32_t serial, uint32_t dir) {
    (void)data; (void)input; (void)serial; (void)dir;
}
static const struct zwp_text_input_v1_listener listener = {
    .enter=entered, .leave=left, .modifiers_map=modifier_map, .input_panel_state=panel_state,
    .preedit_string=preedit_string, .preedit_styling=preedit_style, .preedit_cursor=preedit_cursor,
    .commit_string=commit_string, .cursor_position=cursor_position,
    .delete_surrounding_text=delete_text, .keysym=keysym, .language=language, .text_direction=direction
};
static void global(void *data, struct wl_registry *registry, uint32_t name, const char *interface, uint32_t version) {
    (void)version;
    T630IM *im = data;
    if (!strcmp(interface,"zwp_text_input_manager_v1") && !im->manager)
        im->manager = wl_registry_bind(registry,name,&zwp_text_input_manager_v1_interface,1);
}
static void global_remove(void *data, struct wl_registry *registry, uint32_t name) {
    (void)data; (void)registry; (void)name;
}
static const struct wl_registry_listener registry_listener = { global, global_remove };
static void update_state(T630IM *im) {
    if (!im->active) return;
    GtkInputPurpose purpose;
    g_object_get(im,"input-purpose",&purpose,NULL);
    uint32_t wire_purpose = ZWP_TEXT_INPUT_V1_CONTENT_PURPOSE_NORMAL;
    if (purpose>=GTK_INPUT_PURPOSE_ALPHA && purpose<=GTK_INPUT_PURPOSE_PASSWORD)
        wire_purpose = (uint32_t)purpose;
    else if (purpose==GTK_INPUT_PURPOSE_PIN) wire_purpose = ZWP_TEXT_INPUT_V1_CONTENT_PURPOSE_DIGITS;
    else if (purpose==GTK_INPUT_PURPOSE_TERMINAL) wire_purpose = ZWP_TEXT_INPUT_V1_CONTENT_PURPOSE_TERMINAL;
    zwp_text_input_v1_set_content_type(im->input,private_field(im) ?
        ZWP_TEXT_INPUT_V1_CONTENT_HINT_PASSWORD : ZWP_TEXT_INPUT_V1_CONTENT_HINT_NONE,wire_purpose);
    gboolean handled = FALSE;
    g_signal_emit_by_name(im,"retrieve-surrounding",&handled);
    if (private_field(im) || !im->surrounding)
        zwp_text_input_v1_set_surrounding_text(im->input,"",0,0);
    else
        zwp_text_input_v1_set_surrounding_text(im->input,im->surrounding,im->surrounding_cursor,im->surrounding_cursor);
    zwp_text_input_v1_commit_state(im->input,++im->serial);
}
static void focus_in(GtkIMContext *context) {
    T630IM *im = (T630IM *)context;
    im->focused = TRUE;
    if (!im->window || gdk_window_is_destroyed(im->window) ||
        !GDK_IS_WAYLAND_DISPLAY(gdk_window_get_display(im->window))) return;
    GdkDisplay *display = gdk_window_get_display(im->window);
    if (!im->registry) {
        struct wl_display *wl = gdk_wayland_display_get_wl_display(display);
        im->registry = wl_display_get_registry(wl);
        wl_registry_add_listener(im->registry,&registry_listener,im);
        if (wl_display_roundtrip(wl)<0) return;
    }
    if (!im->manager) return;
    if (!im->input) {
        im->input = zwp_text_input_manager_v1_create_text_input(im->manager);
        zwp_text_input_v1_add_listener(im->input,&listener,im);
    }
    im->seat = gdk_wayland_seat_get_wl_seat(gdk_display_get_default_seat(display));
    GdkWindow *top = gdk_window_get_effective_toplevel(im->window);
    struct wl_surface *surface = gdk_wayland_window_get_wl_surface(top);
    if (surface && im->seat) zwp_text_input_v1_activate(im->input,im->seat,surface);
}
static void focus_out(GtkIMContext *context) {
    T630IM *im = (T630IM *)context;
    gchar *pending = g_strdup(im->preedit_commit);
    clear_preedit(im);
    if (pending && *pending && g_utf8_validate(pending,-1,NULL))
        g_signal_emit_by_name(im,"commit",pending);
    g_free(pending);
    if (im->input && im->seat && im->focused) {
        zwp_text_input_v1_hide_input_panel(im->input);
        zwp_text_input_v1_deactivate(im->input,im->seat);
    }
    im->focused = im->active = FALSE;
    im->delete_length = 0;
}
static void client_window(GtkIMContext *context, GdkWindow *window) {
    T630IM *im = (T630IM *)context;
    if (im->window == window) return;
    gboolean was_focused = im->focused;
    if (was_focused) focus_out(context);
    g_set_object(&im->window,window);
    if (was_focused && window) focus_in(context);
}
static void get_preedit(GtkIMContext *context, gchar **str, PangoAttrList **attrs, gint *cursor) {
    T630IM *im = (T630IM *)context;
    if (!im->preedit) {
        GTK_IM_CONTEXT_CLASS(t630_im_parent_class)->get_preedit_string(context,str,attrs,cursor);
        return;
    }
    const char *text = im->preedit ? im->preedit : "";
    gsize length = strlen(text);
    if (str) *str = g_strdup(text);
    if (attrs) {
        *attrs = pango_attr_list_new();
        if (length) {
            PangoAttribute *attr = pango_attr_underline_new(PANGO_UNDERLINE_SINGLE);
            attr->start_index = 0; attr->end_index = length;
            pango_attr_list_insert(*attrs,attr);
        }
    }
    if (cursor) {
        gint byte = CLAMP(im->preedit_cursor,0,(gint)length);
        *cursor = g_utf8_validate(text,byte,NULL) ? g_utf8_strlen(text,byte) : g_utf8_strlen(text,-1);
    }
}
static void surrounding(GtkIMContext *context, const gchar *text, gint length, gint cursor) {
    T630IM *im = (T630IM *)context;
    g_clear_pointer(&im->surrounding,g_free);
    if (length<0) length = strlen(text);
    if (!private_field(im) && cursor>=0 && cursor<=length && length<=16384 &&
        g_utf8_validate(text,length,NULL) && g_utf8_validate(text,cursor,NULL)) {
        im->surrounding = g_strndup(text,length); im->surrounding_cursor = cursor;
    }
}
static void cursor_rect(GtkIMContext *context, GdkRectangle *rect) {
    T630IM *im = (T630IM *)context;
    if (!im->active || !im->window) return;
    double x=rect->x,y=rect->y;
    GdkWindow *window = im->window, *top = gdk_window_get_effective_toplevel(window);
    while (window && window!=top) {
        gdk_window_coords_to_parent(window,x,y,&x,&y);
        window = gdk_window_get_effective_parent(window);
    }
    zwp_text_input_v1_set_cursor_rectangle(im->input,(int)x,(int)y,rect->width,rect->height);
    update_state(im);
}
static void reset(GtkIMContext *context) {
    T630IM *im = (T630IM *)context;
    gchar *pending = g_strdup(im->preedit_commit);
    clear_preedit(im);
    if (pending && *pending && g_utf8_validate(pending,-1,NULL))
        g_signal_emit_by_name(im,"commit",pending);
    g_free(pending);
    GtkIMContextClass *parent = GTK_IM_CONTEXT_CLASS(t630_im_parent_class);
    if (parent->reset) parent->reset(context);
    if (im->active) {
        zwp_text_input_v1_reset(im->input);
        im->reset_serial = ++im->serial;
        zwp_text_input_v1_commit_state(im->input,im->serial);
    }
}
static void finalize(GObject *object) {
    T630IM *im = (T630IM *)object;
    if (im->input) zwp_text_input_v1_destroy(im->input);
    if (im->manager) zwp_text_input_manager_v1_destroy(im->manager);
    if (im->registry) wl_registry_destroy(im->registry);
    g_clear_object(&im->window);
    g_free(im->preedit); g_free(im->preedit_commit); g_free(im->surrounding);
    G_OBJECT_CLASS(t630_im_parent_class)->finalize(object);
}
static void t630_im_init(T630IM *im) { (void)im; }
static void t630_im_class_finalize(T630IMClass *klass) { (void)klass; }
static void t630_im_class_init(T630IMClass *klass) {
    GtkIMContextClass *context = GTK_IM_CONTEXT_CLASS(klass);
    context->set_client_window = client_window;
    context->focus_in = focus_in; context->focus_out = focus_out;
    context->get_preedit_string = get_preedit; context->set_surrounding = surrounding;
    context->set_cursor_location = cursor_rect; context->reset = reset;
    G_OBJECT_CLASS(klass)->finalize = finalize;
}
static const GtkIMContextInfo info = { "t630-wayland", "Tablet on-screen keyboard", "gtk30", "/usr/share/locale", "" };
static const GtkIMContextInfo *infos[] = { &info };
G_MODULE_EXPORT void im_module_init(GTypeModule *module) { t630_im_register_type(module); }
G_MODULE_EXPORT void im_module_exit(void) {}
G_MODULE_EXPORT void im_module_list(const GtkIMContextInfo ***contexts, int *count) { *contexts=infos; *count=1; }
G_MODULE_EXPORT GtkIMContext *im_module_create(const gchar *id) {
    return !strcmp(id,"t630-wayland") ? g_object_new(t630_im_get_type(),NULL) : NULL;
}
