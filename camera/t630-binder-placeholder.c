#include <android/binder_ibinder.h>
#include <android/binder_parcel.h>
#include <android/binder_status.h>
#include <stdio.h>
#include <stdlib.h>

binder_status_t AServiceManager_addService(AIBinder *binder, const char *instance);
void ABinderProcess_setThreadPoolMaxThreadCount(uint32_t num_threads);
void ABinderProcess_startThreadPool(void);
void ABinderProcess_joinThreadPool(void);

static void *create_service(void *args) {
    return args;
}

static void destroy_service(void *args) {
    (void)args;
}

static binder_status_t transact_service(AIBinder *binder, transaction_code_t code,
                                        const AParcel *input, AParcel *output) {
    (void)binder;
    (void)input;
    fprintf(stderr, "placeholder transaction %u\n", code);

    /*
     * Android 15's AIDL ISurfaceComposer transaction 2 is
     * createDisplayEventConnection(). CameraService asks for one while it
     * builds its dummy BufferQueue. There is no display scheduler in this
     * compatibility environment, so return a valid successful AIDL reply with
     * a nullable (null) connection instead of UNKNOWN_TRANSACTION. The null
     * object is explicitly allowed by the interface.
     */
    if (code == 2 && output != NULL) {
        AStatus *status = AStatus_newOk();
        if (status == NULL) return STATUS_NO_MEMORY;
        binder_status_t result = AParcel_writeStatusHeader(output, status);
        AStatus_delete(status);
        if (result != STATUS_OK) return result;
        return AParcel_writeStrongBinder(output, NULL);
    }
    return STATUS_UNKNOWN_TRANSACTION;
}

int main(int argc, char **argv) {
    const char *service_name = argc > 1 ? argv[1] : "SurfaceFlingerAIDL";
    const char *descriptor = argc > 2 ? argv[2] : "android.ui.ISurfaceComposer";
    AIBinder_Class *service_class = AIBinder_Class_define(
        descriptor, create_service, destroy_service, transact_service);
    if (service_class == NULL) {
        fprintf(stderr, "cannot define binder class\n");
        return 1;
    }
    AIBinder *binder = AIBinder_new(service_class, NULL);
    if (binder == NULL) {
        fprintf(stderr, "cannot create binder\n");
        return 1;
    }
    binder_status_t status = AServiceManager_addService(binder, service_name);
    if (status != STATUS_OK) {
        fprintf(stderr, "cannot register %s: %d\n", service_name, status);
        AIBinder_decStrong(binder);
        return 1;
    }
    fprintf(stderr, "registered placeholder %s (%s)\n", service_name, descriptor);
    ABinderProcess_setThreadPoolMaxThreadCount(4);
    ABinderProcess_startThreadPool();
    ABinderProcess_joinThreadPool();
    AIBinder_decStrong(binder);
    return 0;
}
