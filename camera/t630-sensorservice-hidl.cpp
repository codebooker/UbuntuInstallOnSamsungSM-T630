// SPDX-License-Identifier: MIT
// Register Android's framework sensor-service HIDL adapter without SystemServer.
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include <string>

namespace {

template <typename T>
T symbol(void* library, const char* name) {
    dlerror();
    void* address = dlsym(library, name);
    const char* error = dlerror();
    if (error != nullptr) {
        fprintf(stderr, "dlsym(%s): %s\n", name, error);
        exit(1);
    }
    return reinterpret_cast<T>(address);
}

}  // namespace

int main() {
    void* hidlbase = dlopen("libhidlbase.so", RTLD_NOW | RTLD_GLOBAL);
    void* sensor_interface =
        dlopen("android.frameworks.sensorservice@1.0.so", RTLD_NOW | RTLD_GLOBAL);
    void* sensor_implementation =
        dlopen("libsensorservicehidl.so", RTLD_NOW | RTLD_GLOBAL);
    if (hidlbase == nullptr || sensor_interface == nullptr ||
        sensor_implementation == nullptr) {
        fprintf(stderr, "unable to load sensor-service libraries: %s\n", dlerror());
        return 1;
    }

    using ConfigureRpcThreadpool = void (*)(size_t, bool);
    using JoinRpcThreadpool = void (*)();
    using SensorManagerConstructor = void (*)(void*, void*);
    using RegisterAsService = int32_t (*)(void*, const std::string&);

    auto configure = symbol<ConfigureRpcThreadpool>(
        hidlbase, "_ZN7android8hardware22configureRpcThreadpoolEmb");
    auto join = symbol<JoinRpcThreadpool>(
        hidlbase, "_ZN7android8hardware17joinRpcThreadpoolEv");
    auto construct = symbol<SensorManagerConstructor>(
        sensor_implementation,
        "_ZN7android10frameworks13sensorservice4V1_014implementation13SensorManagerC1EP7_JavaVM");
    auto register_service = symbol<RegisterAsService>(
        sensor_interface,
        "_ZN7android10frameworks13sensorservice4V1_014ISensorManager17registerAsServiceERKNSt3__112basic_stringIcNS4_11char_traitsIcEENS4_9allocatorIcEEEE");

    // The implementation is an ordinary RefBase-derived C++ object.  Reserve
    // substantially more storage than this Android release's class requires;
    // the constructor and implementation both come from the same stock image.
    void* storage = aligned_alloc(64, 4096);
    if (storage == nullptr) {
        perror("aligned_alloc");
        return 1;
    }

    configure(4, true);
    construct(storage, nullptr);
    int32_t status = register_service(storage, "default");
    if (status != 0) {
        fprintf(stderr, "registerAsService failed: %d\n", status);
        return 1;
    }

    puts("registered android.frameworks.sensorservice@1.0::ISensorManager/default");
    fflush(stdout);
    join();
    return 1;
}
