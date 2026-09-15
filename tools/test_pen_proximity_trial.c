#include <assert.h>
#include "t630_pen_proximity_trial.c"
static int event_types[16], events, refs, unrefs, motions, touches;
static const char *name = "xwayland-tablet stylus:14";
static uint64_t serial = 630;
static const char *get_name(void *d) { assert(d); return name; }
static uint64_t get_serial(void *t) { assert(t); return serial; }
static void *ref(void *p) { refs++; return p; }
static void unref(void *p) { assert(p); unrefs++; }
static void *prox(int type, int flags, int64_t time, void *d, void *t) {
    assert(flags == 1 && time == 123 && d && t);
    event_types[events++] = type; return (void *)3;
}
static void put(const void *p) { assert(p == (void *)3); }
static void free_e(void *p) { assert(p == (void *)3); }
static double data[6];
static int constructed_mode, changed_objects, unchanged_objects;
static const char *get_type_name(uintptr_t t) { assert(t == 42); return "MetaInputDeviceX11"; }
static void inspect_constructor(const char *p, va_list args) {
#define EXPECT(k, t, v) do { assert(p && !strcmp(p,k)); assert(va_arg(args,t) == (v)); p=va_arg(args,const char *); } while(0)
    EXPECT("backend", void *, (void *)8);
    assert(!strcmp(p,"name")); assert(va_arg(args,const char *) == name); p=va_arg(args,const char *);
    EXPECT("id",int,11); EXPECT("has-cursor",int,0); EXPECT("device-type",int,5);
    EXPECT("capabilities",unsigned,4);
    assert(!strcmp(p,"device-mode")); constructed_mode=va_arg(args,int); p=va_arg(args,const char *);
    EXPECT("vendor-id",const char *,NULL); EXPECT("product-id",const char *,NULL);
    EXPECT("device-node",const char *,NULL); EXPECT("n-rings",unsigned,0);
    EXPECT("n-strips",unsigned,0); EXPECT("n-mode-groups",unsigned,0);
    EXPECT("seat",void *,(void *)9); assert(!p);
#undef EXPECT
}
static void *new_object(uintptr_t t, const char *p, ...) {
    assert(t==42); va_list args; va_start(args,p); inspect_constructor(p,args); va_end(args);
    changed_objects++; return (void *)10;
}
static void *new_valist(uintptr_t t, const char *p, va_list args) {
    assert(t==42); inspect_constructor(p,args); unchanged_objects++; return (void *)10;
}
static void send_constructor(void) {
    assert(g_object_new(42,"backend",(void *)8,"name",name,"id",11,"has-cursor",0,
        "device-type",5,"capabilities",4U,"device-mode",1,"vendor-id",NULL,
        "product-id",NULL,"device-node",NULL,"n-rings",0U,"n-strips",0U,
        "n-mode-groups",0U,"seat",(void *)9,NULL) == (void *)10);
}
static void *motion(int f, int64_t t, void *d, void *tool, int m,
                    Point c, Point delta, Point raw, Point constrained, double *a) {
    assert(f == 7 && t == 123 && d == (void *)1 && tool == (void *)2 && m == 9);
    assert(c.x == 10 && c.y == 20 && delta.x == 30 && raw.x == 40 && constrained.x == 50);
    assert(a == data); motions++; return (void *)4;
}
static void *touch(int type, int f, int64_t t, void *d, void *seq, int m, Point c) {
    assert(type == 12 && f == 7 && t == 123 && d == (void *)5 && seq == (void *)6);
    assert(m == 9 && c.x == 10 && c.y == 20); touches++; return (void *)7;
}
static void send_motion(void) {
    assert(clutter_event_motion_new(7,123,(void *)1,(void *)2,9,
        (Point){10,20},(Point){30,0},(Point){40,0},(Point){50,0},data) == (void *)4);
}
int main(void) {
    initialized = 1; enabled = 1;
    next_motion = motion; next_touch = touch; proximity = prox;
    device_name = get_name; tool_serial = get_serial;
    object_ref = ref; object_unref = unref; put_event = put; free_event = free_e;
    next_object_new=new_object; next_object_valist=new_valist; type_name=get_type_name;
    send_constructor(); assert(constructed_mode==2 && changed_objects==1 && unchanged_objects==0);
    name="xwayland-tablet stylus:14bad"; send_constructor();
    assert(constructed_mode==1 && unchanged_objects==1);
    name="mouse"; send_constructor(); assert(constructed_mode==1 && unchanged_objects==2);
    name="xwayland-tablet stylus:14";
    send_motion(); send_motion();
    assert(events == 1 && event_types[0] == 16 && refs == 2 && unrefs == 0 && motions == 2);
    assert(clutter_event_touch_new(12,7,123,(void *)5,(void *)6,9,(Point){10,20}) == (void *)7);
    assert(events == 2 && event_types[1] == 17 && refs == unrefs && touches == 1);
    for (unsigned i = 0; i < 4; i++) {
        const char *bad[] = {"xwayland-tablet stylus:","xwayland-tablet stylus:14bad",
                            "sec_e-pen", "xwayland-tablet cursor:14"};
        name = bad[i]; send_motion(); assert(events == 2);
    }
    name = "xwayland-tablet eraser:14"; serial = 631;
    send_motion(); assert(events == 2);
    serial = 630; send_motion(); assert(events == 3 && event_types[2] == 16);
    name = "mouse"; send_motion(); assert(events == 4 && event_types[3] == 17 && refs == unrefs);
    name = "xwayland-tablet stylus:14"; enabled = 0;
    send_motion(); assert(events == 4);
    return 0;
}
