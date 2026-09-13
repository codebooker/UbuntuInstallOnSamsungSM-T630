/* Work around incomplete large software-rendered XPutImage transfers.
 * Scoped to the nested GNOME session, never the physical compositor.
 * Keep ZPixmap requests below the base X11 request-size limit. Other formats
 * and layouts are passed through. No image or input contents are logged.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <limits.h>
#include <stdlib.h>
#include <stdio.h>
#include <xcb/xcb.h>

typedef xcb_void_cookie_t (*put_fn)(xcb_connection_t *, uint8_t,
    xcb_drawable_t, xcb_gcontext_t, uint16_t, uint16_t, int16_t, int16_t,
    uint8_t, uint8_t, uint32_t, const uint8_t *);

xcb_void_cookie_t xcb_put_image(xcb_connection_t *c, uint8_t format,
    xcb_drawable_t drawable, xcb_gcontext_t gc, uint16_t w, uint16_t h,
    int16_t x, int16_t y, uint8_t pad, uint8_t depth, uint32_t size,
    const uint8_t *data)
{
    put_fn next = (put_fn)dlsym(RTLD_NEXT, "xcb_put_image");
    if (!next) abort();
    const uint32_t limit = 240 * 1024;
    const uint32_t stride = (uint32_t)w * 4;
    static unsigned reports;
    if (reports++ < 4) fprintf(stderr,"T630_TRANSFER format=%u pad=%u depth=%u size=%u w=%u h=%u x=%d y=%d\n",format,pad,depth,size,w,h,x,y);
    if (format != XCB_IMAGE_FORMAT_Z_PIXMAP || pad || !w || !h || !data ||
        (depth != 24 && depth != 32) || stride > limit ||
        (uint64_t)stride * h != size || size <= limit ||
        (int32_t)y + h - 1 > INT16_MAX)
        return next(c,format,drawable,gc,w,h,x,y,pad,depth,size,data);

    const uint32_t rows = limit / stride;
    xcb_void_cookie_t result = {0};
    for (uint32_t row = 0; row < h; row += rows) {
        uint16_t count = h - row < rows ? h - row : rows;
        result = next(c,format,drawable,gc,w,count,x,y+row,pad,depth,
                      stride*count,data+stride*row);
    }
    return result;
}
