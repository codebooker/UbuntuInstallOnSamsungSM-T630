#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static uint8_t clip_byte(int value) {
    if (value < 0) return 0;
    if (value > 255) return 255;
    return (uint8_t)value;
}

static int load_color_offset(const char *path) {
    if (path == NULL) return 0;
    FILE *file = fopen(path, "r");
    if (file == NULL) return 0;
    int value = 0;
    int matched = fscanf(file, "%d", &value);
    fclose(file);
    return matched == 1 && value >= -100 && value <= 100 ? value : 0;
}

static int read_frame(uint8_t *buffer, size_t size) {
    size_t offset = 0;
    while (offset < size) {
        ssize_t count = read(STDIN_FILENO, buffer + offset, size - offset);
        if (count == 0) return offset == 0 ? 0 : -1;
        if (count < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        offset += (size_t)count;
    }
    return 1;
}

static int write_frame(const uint8_t *buffer, size_t size) {
    size_t offset = 0;
    while (offset < size) {
        ssize_t count = write(STDOUT_FILENO, buffer + offset, size - offset);
        if (count < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        offset += (size_t)count;
    }
    return 0;
}

static void tune_i420(uint8_t *frame, int width, int height,
                      int red_gain, int blue_gain) {
    const size_t y_size = (size_t)width * (size_t)height;
    uint8_t *y_plane = frame;
    uint8_t *u_plane = frame + y_size;
    uint8_t *v_plane = u_plane + y_size / 4;

    for (int row = 0; row < height; row += 2) {
        for (int column = 0; column < width; column += 2) {
            const size_t chroma = (size_t)(row / 2) * (size_t)(width / 2) +
                                  (size_t)(column / 2);
            const int d = (int)u_plane[chroma] - 128;
            const int e = (int)v_plane[chroma] - 128;
            int u_sum = 0;
            int v_sum = 0;

            for (int dy = 0; dy < 2; ++dy) {
                for (int dx = 0; dx < 2; ++dx) {
                    const size_t pixel = (size_t)(row + dy) * (size_t)width +
                                         (size_t)(column + dx);
                    int c = (int)y_plane[pixel] - 16;
                    if (c < 0) c = 0;
                    int red = clip_byte((298 * c + 409 * e + 128) >> 8);
                    int green = clip_byte((298 * c - 100 * d - 208 * e + 128) >> 8);
                    int blue = clip_byte((298 * c + 516 * d + 128) >> 8);
                    red = clip_byte((red * red_gain + 500) / 1000);
                    blue = clip_byte((blue * blue_gain + 500) / 1000);

                    y_plane[pixel] = clip_byte(
                        ((66 * red + 129 * green + 25 * blue + 128) >> 8) + 16);
                    u_sum += ((-38 * red - 74 * green + 112 * blue + 128) >> 8) + 128;
                    v_sum += ((112 * red - 94 * green - 18 * blue + 128) >> 8) + 128;
                }
            }
            u_plane[chroma] = clip_byte((u_sum + 2) / 4);
            v_plane[chroma] = clip_byte((v_sum + 2) / 4);
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 5 && argc != 6) {
        fprintf(stderr,
                "usage: %s width height red-permille blue-permille [color-offset-file]\n",
                argv[0]);
        return 2;
    }
    const int width = atoi(argv[1]);
    const int height = atoi(argv[2]);
    const int red_gain = atoi(argv[3]);
    const int blue_gain = atoi(argv[4]);
    const char *settings_path = argc == 6 ? argv[5] : NULL;
    if (width < 2 || height < 2 || width % 2 != 0 || height % 2 != 0 ||
        red_gain < 500 || red_gain > 2000 ||
        blue_gain < 500 || blue_gain > 2000) {
        fprintf(stderr, "invalid dimensions or channel gain\n");
        return 2;
    }

    const size_t frame_size = (size_t)width * (size_t)height * 3 / 2;
    uint8_t *frame = malloc(frame_size);
    if (frame == NULL) return 1;
    signal(SIGPIPE, SIG_IGN);

    int status = 0;
    unsigned int frame_number = 0;
    int color_offset = 0;
    for (;;) {
        int input = read_frame(frame, frame_size);
        if (input == 0) break;
        if (input < 0) {
            fprintf(stderr, "truncated I420 frame\n");
            status = 1;
            break;
        }
        if (frame_number % 15 == 0) {
            int updated = load_color_offset(settings_path);
            if (frame_number == 0 || updated != color_offset) {
                color_offset = updated;
                fprintf(stderr, "color tuning: offset=%d red=%d blue=%d\n",
                        color_offset, red_gain - color_offset,
                        blue_gain + 3 * color_offset);
            }
        }
        tune_i420(frame, width, height, red_gain - color_offset,
                  blue_gain + 3 * color_offset);
        if (write_frame(frame, frame_size) != 0) break;
        frame_number++;
    }
    free(frame);
    return status;
}
