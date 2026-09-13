/* Preview rendering diagnostics; optional bounded XPutImage chunking test. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <xcb/xcb.h>
xcb_void_cookie_t xcb_put_image(xcb_connection_t *c, uint8_t format,
        xcb_drawable_t drawable, xcb_gcontext_t gc, uint16_t w, uint16_t h,
        int16_t x, int16_t y, uint8_t pad, uint8_t depth, uint32_t size,
        const uint8_t *data) {
    static xcb_void_cookie_t (*next)(xcb_connection_t *,uint8_t,xcb_drawable_t,
        xcb_gcontext_t,uint16_t,uint16_t,int16_t,int16_t,uint8_t,uint8_t,
        uint32_t,const uint8_t *);
    static int count;
    if (!next) next=dlsym(RTLD_NEXT,"xcb_put_image");
    if (count++ < 30) {
        fprintf(stderr,"T630_XPUT drawable=%x size=%ux%u at=%d,%d bytes=%u depth=%u\n",drawable,w,h,x,y,size,depth);
        if (w==1600 && h==1000 && size==6400000) {
            unsigned int a=(100*w+800)*4,b=(850*w+800)*4;
            fprintf(stderr,"T630_XPUT pixels top=%u,%u,%u bottom=%u,%u,%u\n",data[a],data[a+1],data[a+2],data[b],data[b+1],data[b+2]);
        }
    }
    if (getenv("T630_SPLIT_XPUT") && format==XCB_IMAGE_FORMAT_Z_PIXMAP &&
        pad==0 && depth==24 && w==1600 && h==1000 && x==0 && y==0 &&
        size==6400000) {
        xcb_void_cookie_t result={0};
        for (unsigned row=0; row<h; row+=100)
            result=next(c,format,drawable,gc,w,100,x,(int16_t)row,pad,
                        depth,w*100*4,data+row*w*4);
        return result;
    }
    return next(c,format,drawable,gc,w,h,x,y,pad,depth,size,data);
}
void cogl_onscreen_swap_buffers(void *screen, void *info, void *frame) {
    static void (*next)(void *,void *,void *);
    static int count;
    if (!next) next = dlsym(RTLD_NEXT, "cogl_onscreen_swap_buffers");
    if (count++ < 4) {
        int (*width)(void *) = dlsym(RTLD_NEXT,"cogl_framebuffer_get_width");
        int (*height)(void *) = dlsym(RTLD_NEXT,"cogl_framebuffer_get_height");
        void *(*display)(void) = dlsym(RTLD_DEFAULT,"eglGetCurrentDisplay");
        void *(*surface)(int) = dlsym(RTLD_DEFAULT,"eglGetCurrentSurface");
        int (*query)(void *,void *,int,int *) = dlsym(RTLD_DEFAULT,"eglQuerySurface");
        void (*getint)(unsigned,int *) = dlsym(RTLD_DEFAULT,"glGetIntegerv");
        void (*readpix)(int,int,int,int,unsigned,unsigned,void *) = dlsym(RTLD_DEFAULT,"glReadPixels");
        unsigned char (*enabled)(unsigned) = dlsym(RTLD_DEFAULT,"glIsEnabled");
        int w=-1,h=-1,v[4]={-1,-1,-1,-1};
        if (query && display && surface) {
            query(display(),surface(0x3059),0x3057,&w);
            query(display(),surface(0x3059),0x3056,&h);
        }
        if (getint) getint(0x0BA2,v);
        fprintf(stderr,"T630_PROBE framebuffer=%dx%d egl=%dx%d viewport=%d,%d,%d,%d\n",
            width(screen),height(screen),w,h,v[0],v[1],v[2],v[3]);
        int box[4]={0},fbo=-1;
        unsigned char bottom[4]={0},top[4]={0};
        if (getint) {getint(0x0C10,box);getint(0x8CA6,&fbo);}
        if (readpix) {
            readpix(800,150,1,1,0x1908,0x1401,bottom);
            readpix(800,800,1,1,0x1908,0x1401,top);
        }
        fprintf(stderr,"T630_PROBE scissor=%d:%d,%d,%d,%d fbo=%d bottom=%u,%u,%u top=%u,%u,%u\n",
            enabled ? enabled(0x0C11) : -1,box[0],box[1],box[2],box[3],fbo,
            bottom[0],bottom[1],bottom[2],top[0],top[1],top[2]);
    }
    next(screen,info,frame);
}
