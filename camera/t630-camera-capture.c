#include <camera/NdkCameraDevice.h>
#include <camera/NdkCameraManager.h>
#include <media/NdkImage.h>
#include <media/NdkImageReader.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Exported by Android's libbinder_ndk; the public NDK omits this header. */
void ABinderProcess_startThreadPool(void);
void ABinderProcess_setThreadPoolMaxThreadCount(uint32_t num_threads);

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition = PTHREAD_COND_INITIALIZER;
static int frame_result = 0;
static int frame_claimed = 0;
static const char *output_path;

static void finish(int result) {
    pthread_mutex_lock(&lock);
    if (frame_result == 0) {
        frame_result = result;
        pthread_cond_signal(&condition);
    }
    pthread_mutex_unlock(&lock);
}

static void image_available(void *context, AImageReader *reader) {
    (void)context;
    AImage *image = NULL;
    media_status_t status = AImageReader_acquireLatestImage(reader, &image);
    if (status != AMEDIA_OK || image == NULL) {
        fprintf(stderr, "acquire image failed: %d\n", status);
        return;
    }

    /* More than one Binder worker may receive an image callback before the
     * main thread closes the repeating request. Claim exactly one frame so
     * concurrent callbacks cannot truncate and rewrite the same output. */
    pthread_mutex_lock(&lock);
    if (frame_claimed || frame_result != 0) {
        pthread_mutex_unlock(&lock);
        AImage_delete(image);
        return;
    }
    frame_claimed = 1;
    pthread_mutex_unlock(&lock);

    int32_t width = 0, height = 0, row_stride = 0, pixel_stride = 0;
    uint8_t *data = NULL;
    int data_length = 0;
    if (AImage_getWidth(image, &width) != AMEDIA_OK ||
        AImage_getHeight(image, &height) != AMEDIA_OK ||
        AImage_getPlaneRowStride(image, 0, &row_stride) != AMEDIA_OK ||
        AImage_getPlanePixelStride(image, 0, &pixel_stride) != AMEDIA_OK ||
        AImage_getPlaneData(image, 0, &data, &data_length) != AMEDIA_OK) {
        fprintf(stderr, "reading image plane failed\n");
        AImage_delete(image);
        finish(-1);
        return;
    }

    FILE *file = fopen(output_path, "wb");
    if (file == NULL) {
        perror("opening output");
        AImage_delete(image);
        finish(-1);
        return;
    }
    fprintf(file, "P5\n%d %d\n255\n", width, height);
    for (int y = 0; y < height; ++y) {
        uint8_t *row = data + y * row_stride;
        if (pixel_stride == 1) {
            fwrite(row, 1, width, file);
        } else {
            for (int x = 0; x < width; ++x) {
                fputc(row[x * pixel_stride], file);
            }
        }
    }
    fclose(file);
    fprintf(stderr, "captured %dx%d Y frame to %s\n", width, height, output_path);
    AImage_delete(image);
    finish(1);
}

static void camera_disconnected(void *context, ACameraDevice *device) {
    (void)context;
    (void)device;
    fprintf(stderr, "camera disconnected\n");
    finish(-1);
}

static void camera_error(void *context, ACameraDevice *device, int error) {
    (void)context;
    (void)device;
    fprintf(stderr, "camera error: %d\n", error);
    finish(-1);
}

static void session_closed(void *context, ACameraCaptureSession *session) {
    (void)context;
    (void)session;
    fprintf(stderr, "session closed\n");
}

static void session_ready(void *context, ACameraCaptureSession *session) {
    (void)context;
    (void)session;
    fprintf(stderr, "session ready\n");
}

static void session_active(void *context, ACameraCaptureSession *session) {
    (void)context;
    (void)session;
    fprintf(stderr, "session active\n");
}

static void capture_started(void *context, ACameraCaptureSession *session,
                            const ACaptureRequest *request, int64_t timestamp) {
    (void)context;
    (void)session;
    (void)request;
    fprintf(stderr, "capture started at %lld\n", (long long)timestamp);
}

static void capture_progressed(void *context, ACameraCaptureSession *session,
                               ACaptureRequest *request,
                               const ACameraMetadata *result) {
    (void)context;
    (void)session;
    (void)request;
    (void)result;
    fprintf(stderr, "capture progressed\n");
}

static void capture_completed(void *context, ACameraCaptureSession *session,
                              ACaptureRequest *request,
                              const ACameraMetadata *result) {
    (void)context;
    (void)session;
    (void)request;
    (void)result;
    fprintf(stderr, "capture completed\n");
}

static void capture_failed(void *context, ACameraCaptureSession *session,
                           ACaptureRequest *request,
                           ACameraCaptureFailure *failure) {
    (void)context;
    (void)session;
    (void)request;
    fprintf(stderr,
            "capture failed: frame=%lld reason=%d sequence=%d image=%d\n",
            (long long)failure->frameNumber, failure->reason,
            failure->sequenceId, failure->wasImageCaptured);
    finish(-1);
}

static void capture_sequence_completed(void *context,
                                       ACameraCaptureSession *session,
                                       int sequence_id, int64_t frame_number) {
    (void)context;
    (void)session;
    fprintf(stderr, "capture sequence %d completed at frame %lld\n",
            sequence_id, (long long)frame_number);
}

static void capture_sequence_aborted(void *context,
                                     ACameraCaptureSession *session,
                                     int sequence_id) {
    (void)context;
    (void)session;
    fprintf(stderr, "capture sequence %d aborted\n", sequence_id);
    finish(-1);
}

static void capture_buffer_lost(void *context,
                                ACameraCaptureSession *session,
                                ACaptureRequest *request,
                                ANativeWindow *window,
                                int64_t frame_number) {
    (void)context;
    (void)session;
    (void)request;
    (void)window;
    fprintf(stderr, "capture buffer lost at frame %lld\n",
            (long long)frame_number);
}

static int check_status(const char *operation, camera_status_t status) {
    if (status == ACAMERA_OK) return 0;
    fprintf(stderr, "%s failed: %d\n", operation, status);
    return -1;
}

int main(int argc, char **argv) {
    const char *camera_id = argc > 1 ? argv[1] : "0";
    output_path = argc > 2 ? argv[2] : "/data/vendor/camera/t630-frame.pgm";
    int width = argc > 3 ? atoi(argv[3]) : 640;
    int height = argc > 4 ? atoi(argv[4]) : 480;
    int max_images = argc > 5 ? atoi(argv[5]) : 16;
    int timeout_seconds = argc > 6 ? atoi(argv[6]) : 60;
    int result = 1;

    /*
     * AImageReader's BufferQueue producer lives in cameraserver.  A standalone
     * native process must service incoming Binder transactions itself; Android
     * applications normally get this thread pool from the runtime.
     */
    ABinderProcess_setThreadPoolMaxThreadCount(8);
    ABinderProcess_startThreadPool();

    ACameraManager *manager = ACameraManager_create();
    ACameraIdList *ids = NULL;
    camera_status_t camera_status = ACameraManager_getCameraIdList(manager, &ids);
    if (check_status("get camera list", camera_status) != 0) goto done;
    fprintf(stderr, "available cameras:");
    for (int i = 0; i < ids->numCameras; ++i) fprintf(stderr, " %s", ids->cameraIds[i]);
    fprintf(stderr, "\nopening camera %s\n", camera_id);

    AImageReader *reader = NULL;
    fprintf(stderr, "image reader: %dx%d, %d buffers, %ds timeout\n",
            width, height, max_images, timeout_seconds);
    media_status_t media_status = AImageReader_new(width, height, AIMAGE_FORMAT_YUV_420_888,
                                                   max_images, &reader);
    if (media_status != AMEDIA_OK) {
        fprintf(stderr, "create image reader failed: %d\n", media_status);
        goto done;
    }
    AImageReader_ImageListener image_listener = { .context = NULL, .onImageAvailable = image_available };
    AImageReader_setImageListener(reader, &image_listener);
    ANativeWindow *window = NULL;
    AImageReader_getWindow(reader, &window);

    ACameraDevice *device = NULL;
    ACameraDevice_StateCallbacks device_callbacks = {
        .context = NULL,
        .onDisconnected = camera_disconnected,
        .onError = camera_error,
    };
    camera_status = ACameraManager_openCamera(manager, camera_id, &device_callbacks, &device);
    if (check_status("open camera", camera_status) != 0) goto cleanup_reader;

    ACameraOutputTarget *target = NULL;
    ACaptureSessionOutput *session_output = NULL;
    ACaptureSessionOutputContainer *outputs = NULL;
    ACaptureRequest *request = NULL;
    ACameraCaptureSession *session = NULL;
    if (check_status("create target", ACameraOutputTarget_create(window, &target)) != 0 ||
        check_status("create session output", ACaptureSessionOutput_create(window, &session_output)) != 0 ||
        check_status("create output container", ACaptureSessionOutputContainer_create(&outputs)) != 0 ||
        check_status("add output", ACaptureSessionOutputContainer_add(outputs, session_output)) != 0 ||
        check_status("create request", ACameraDevice_createCaptureRequest(device, TEMPLATE_STILL_CAPTURE, &request)) != 0 ||
        check_status("add target", ACaptureRequest_addTarget(request, target)) != 0) {
        goto cleanup_camera;
    }

    ACameraCaptureSession_stateCallbacks session_callbacks = {
        .context = NULL,
        .onClosed = session_closed,
        .onReady = session_ready,
        .onActive = session_active,
    };
    camera_status = ACameraDevice_createCaptureSession(device, outputs, &session_callbacks, &session);
    if (check_status("create capture session", camera_status) != 0) goto cleanup_camera;

    ACameraCaptureSession_captureCallbacks capture_callbacks = {
        .context = NULL,
        .onCaptureStarted = capture_started,
        .onCaptureProgressed = capture_progressed,
        .onCaptureCompleted = capture_completed,
        .onCaptureFailed = capture_failed,
        .onCaptureSequenceCompleted = capture_sequence_completed,
        .onCaptureSequenceAborted = capture_sequence_aborted,
        .onCaptureBufferLost = capture_buffer_lost,
    };
    int sequence_id = 0;
    camera_status = ACameraCaptureSession_setRepeatingRequest(session, &capture_callbacks, 1, &request, &sequence_id);
    if (check_status("start capture", camera_status) != 0) goto cleanup_camera;

    struct timespec deadline;
    clock_gettime(CLOCK_REALTIME, &deadline);
    deadline.tv_sec += timeout_seconds;
    pthread_mutex_lock(&lock);
    while (frame_result == 0) {
        if (pthread_cond_timedwait(&condition, &lock, &deadline) != 0) break;
    }
    result = frame_result == 1 ? 0 : 1;
    pthread_mutex_unlock(&lock);
    if (frame_result == 0) fprintf(stderr, "timed out waiting for frame\n");

cleanup_camera:
    if (session) ACameraCaptureSession_close(session);
    if (request) ACaptureRequest_free(request);
    if (outputs && session_output) ACaptureSessionOutputContainer_remove(outputs, session_output);
    if (session_output) ACaptureSessionOutput_free(session_output);
    if (outputs) ACaptureSessionOutputContainer_free(outputs);
    if (target) ACameraOutputTarget_free(target);
    if (device) ACameraDevice_close(device);
cleanup_reader:
    AImageReader_delete(reader);
done:
    if (ids) ACameraManager_deleteCameraIdList(ids);
    ACameraManager_delete(manager);
    return result;
}
