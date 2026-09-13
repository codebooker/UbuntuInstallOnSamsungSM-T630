/* Mutter 46 + Mesa 25.2.8 EGL/X11 swrast size-refresh workaround.
 * Mesa's swrastPutImage2 clamps to cached _EGLSurface.Height (initially 480).
 * eglQuerySurface refreshes that cache from the actual X drawable geometry.
 * Query before presenting; no pixel readback, image logging or XPutImage hook.
 * Only loaded into the experimental nested GNOME session, not Weston.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
void cogl_onscreen_swap_buffers(void *screen, void *info, void *frame)
{
    void (*next)(void *,void *,void *)=dlsym(RTLD_NEXT,"cogl_onscreen_swap_buffers");
    void *(*display)(void)=dlsym(RTLD_DEFAULT,"eglGetCurrentDisplay");
    void *(*surface)(int)=dlsym(RTLD_DEFAULT,"eglGetCurrentSurface");
    int (*query)(void *,void *,int,int *)=dlsym(RTLD_DEFAULT,"eglQuerySurface");
    if (!next) abort();
    if (display && surface && query) {
        void *dpy=display(), *draw=surface(0x3059); /* EGL_DRAW */
        int width, height;
        if (dpy && draw) {
            query(dpy,draw,0x3057,&width);  /* EGL_WIDTH */
            query(dpy,draw,0x3056,&height); /* EGL_HEIGHT */
        }
    }
    next(screen,info,frame);
}
