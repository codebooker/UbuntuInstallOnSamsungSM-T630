#include <android/binder_ibinder.h>
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
    (void)output;
    fprintf(stderr, "placeholder transaction %u\n", code);
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
        fprintf(stderr, "cannot register %s: %dd\n", service_name, status);
        AIBinder_decStrong(binder);
        return 1;
    }
    fprintf(stderr, "registered placeholder %s (%s\n", service_name, descriptor);
    ABinderProcess_setThreadPoolMaxThreadCount(4);
    ABinderProcess_startThreadPool();
    ABinderProcess_joinThreadPool();
    AIBinder_decStrong(binder);
    return 0;
}
