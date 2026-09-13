/*
 * Read-only Android property shim for preserved SM-T630 camera services.
 *
 * Android's libc normally maps a property area created by Android init. The
 * Ubuntu system deliberately does not run Android init, so expose only the
 * handful of immutable values required to bootstrap the stock camera HAL.
 * This shared object has no libc dependency and is safe to preload first.
 */

#include <stdint.h>

typedef struct t630_property {
    uint32_t serial;
    char value[92];
    char name[96];
} t630_property;

typedef void (*property_read_callback)(void *cookie, const char *name,
                                       const char *value, uint32_t serial);

static const t630_property properties[] = {
    {0x01000001, "2", "ro.property_service.version"},
    {0x04000001, "true", "hwservicemanager.ready"},
    {0x04000001, "true", "servicemanager.ready"},
    {0x0e000001, "gtact4prowifi", "ro.product.device"},
    {0x0e000001, "gtact4prowifi", "ro.product.vendor.device"},
    {0x07000001, "SM-T630", "ro.product.model"},
    {0x07000001, "SM-T630", "ro.product.vendor.model"},
    {0x04000001, "qcom", "ro.hardware"},
    /* Keep BufferQueue allocation in-process when SurfaceFlinger is absent. */
    {0x01000001, "1", "config.headless"},
    {0x07000001, "lahaina", "ro.board.platform"},
    {0x07000001, "lahaina", "ro.product.board"},
    /* Board revision 5 is what the stock bootloader supplies on this unit.
     * Samsung's camera HAL consults it while choosing between the DV1 and DV2
     * S5K3L6 rear-sensor descriptions. */
    {0x01000001, "5", "ro.boot.revision"},
    {0x11000001, "gtact4prowifixx", "ro.product.name"},
    {0x04000001, "user", "ro.build.type"},
    {0x01000001, "0", "ro.debuggable"},
    {0x02000001, "35", "ro.build.version.sdk"},
    {0x02000001, "30", "ro.vendor.build.version.sdk"},
    {0x02000001, "30", "ro.vendor.api_level"},
    {0x02000001, "32", "ro.product.first_api_level"},
};

static long raw_syscall4(long number, long first, long second, long third,
                         long fourth) {
    register long x0 __asm__("x0") = first;
    register long x1 __asm__("x1") = second;
    register long x2 __asm__("x2") = third;
    register long x3 __asm__("x3") = fourth;
    register long x8 __asm__("x8") = number;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x8)
                     : "memory");
    return x0;
}

static unsigned int string_length(const char *text) {
    unsigned int length = 0;
    while (text[length] != '\0') {
        ++length;
    }
    return length;
}

static void log_property(char operation, const char *name) {
    static const char path[] = "/dev/t630-property-reads.log";
    static const char separator[] = " ";
    static const char newline[] = "\n";
    long descriptor = raw_syscall4(56, -100, (long)path, 1089, 0644);
    if (descriptor < 0) {
        return;
    }
    raw_syscall4(64, descriptor, (long)&operation, 1, 0);
    raw_syscall4(64, descriptor, (long)separator, 1, 0);
    raw_syscall4(64, descriptor, (long)name, string_length(name), 0);
    raw_syscall4(64, descriptor, (long)newline, 1, 0);
    raw_syscall4(57, descriptor, 0, 0, 0);
}

static int string_equal(const char *left, const char *right) {
    while (*left != '\0' && *left == *right) {
        ++left;
        ++right;
    }
    return *left == *right;
}

static unsigned int string_copy(char *destination, const char *source) {
    unsigned int length = 0;
    while (source[length] != '\0') {
        destination[length] = source[length];
        ++length;
    }
    destination[length] = '\0';
    return length;
}

static const t630_property *find_property(const char *name) {
    unsigned int index;
    for (index = 0; index < sizeof(properties) / sizeof(properties[0]); ++index) {
        if (string_equal(name, properties[index].name)) {
            return &properties[index];
        }
    }
    return 0;
}

const void *__system_property_find(const char *name) {
    log_property('F', name);
    return find_property(name);
}

void __system_property_read_callback(const void *property,
                                     property_read_callback callback,
                                     void *cookie) {
    const t630_property *entry = (const t630_property *)property;
    if (entry != 0 && callback != 0) {
        callback(cookie, entry->name, entry->value, entry->serial);
    }
}

int __system_property_get(const char *name, char *value) {
    log_property('G', name);
    const t630_property *entry = find_property(name);
    if (entry == 0) {
        if (value != 0) {
            value[0] = '\0';
        }
        return 0;
    }
    return (int)string_copy(value, entry->value);
}

uint32_t __system_property_serial(const void *property) {
    const t630_property *entry = (const t630_property *)property;
    return entry == 0 ? 0 : entry->serial;
}

uint32_t __system_property_area_serial(void) {
    return 1;
}

int __system_property_wait(const void *property, uint32_t old_serial,
                           uint32_t *new_serial, const void *relative_timeout) {
    const t630_property *entry = (const t630_property *)property;
    (void)old_serial;
    (void)relative_timeout;
    if (new_serial != 0) {
        *new_serial = entry == 0 ? 1 : entry->serial;
    }
    return 1;
}

int __system_property_set(const char *name, const char *value) {
    log_property('S', name);
    (void)name;
    (void)value;
    return 0;
}

int property_get(const char *name, char *value, const char *default_value) {
    int length = __system_property_get(name, value);
    if (length == 0 && default_value != 0) {
        return (int)string_copy(value, default_value);
    }
    return length;
}

int property_set(const char *name, const char *value) {
    return __system_property_set(name, value);
}

/*
 * Android's servicemanager expects a live SELinux status page and aborts when
 * booted under the Ubuntu initramfs, where SELinux is intentionally disabled.
 * Report a stable permissive status so Binder services can run in this small
 * compatibility environment.  These are deliberately limited to the status
 * API; the normal Android service-context parser remains in use.
 */
int selinux_status_open(int fallback) {
    (void)fallback;
    return 0;
}

void selinux_status_close(void) {
}

int selinux_status_updated(void) {
    return 0;
}

int selinux_status_getenforce(void) {
    return 0;
}

int selinux_status_policyload(void) {
    return 0;
}

int selinux_status_deny_unknown(void) {
    return 0;
}

/*
 * The stripped-down compatibility environment intentionally does not run
 * Android's Java PermissionCheckerService.  CameraService otherwise waits
 * forever for that service before it will accept a native test client.
 * These ABI-compatible stubs grant the checks performed inside the isolated
 * camera stack; they are preloaded only into these lab services, never GNOME.
 */
int t630_permission_data_delivery(void)
    __asm__("_ZN7android10permission17PermissionChecker44checkPermissionForDataDeliveryFromDatasourceERKNS_8String16ERKNS_7content22AttributionSourceStateES4_i");
int t630_permission_data_delivery(void) { return 0; }

int t630_permission_start_delivery(void)
    __asm__("_ZN7android10permission17PermissionChecker49checkPermissionForStartDataDeliveryFromDatasourceERKNS_8String16ERKNS_7content22AttributionSourceStateES4_i");
int t630_permission_start_delivery(void) { return 0; }

int t630_permission_preflight(void)
    __asm__("_ZN7android10permission17PermissionChecker27checkPermissionForPreflightERKNS_8String16ERKNS_7content22AttributionSourceStateES4_i");
int t630_permission_preflight(void) { return 0; }

int t630_permission_preflight_datasource(void)
    __asm__("_ZN7android10permission17PermissionChecker41checkPermissionForPreflightFromDatasourceERKNS_8String16ERKNS_7content22AttributionSourceStateES4_i");
int t630_permission_preflight_datasource(void) { return 0; }

int t630_permission_check(void)
    __asm__("_ZN7android10permission17PermissionChecker15checkPermissionERKNS_8String16ERKNS_7content22AttributionSourceStateES4_bbbi");
int t630_permission_check(void) { return 0; }

/* CameraService's administrative Binder entry points use libbinder's older
 * checkCallingPermission helpers rather than PermissionChecker. Grant these
 * too so the lab launcher can disable the Android watchdog before opening a
 * device. Both functions return C++ bool (0/1). */
int t630_check_calling_permission(void)
    __asm__("_ZN7android22checkCallingPermissionERKNS_8String16E");
int t630_check_calling_permission(void) { return 1; }

int t630_check_calling_permission_ids(void)
    __asm__("_ZN7android22checkCallingPermissionERKNS_8String16EPiS3_");
int t630_check_calling_permission_ids(void) { return 1; }

void t630_permission_finish(void)
    __asm__("_ZN7android10permission17PermissionChecker32finishDataDeliveryFromDatasourceEiRKNS_7content22AttributionSourceStateE");
void t630_permission_finish(void) {}

/* CameraService also registers each client with Android's Java activity
 * manager.  There is no system_server in this environment, so keep the
 * isolated camera client permanently in the foreground instead. */
int t630_am_add_uid(void)
    __asm__("_ZN7android15ActivityManager16addUidToObserverERKNS_2spINS_7IBinderEEERKNS_8String16Ei");
int t630_am_add_uid(void) { return 0; }

int t630_am_remove_uid(void)
    __asm__("_ZN7android15ActivityManager21removeUidFromObserverERKNS_2spINS_7IBinderEEERKNS_8String16Ei");
int t630_am_remove_uid(void) { return 0; }

int t630_am_is_uid_active(void)
    __asm__("_ZN7android15ActivityManager11isUidActiveEjRKNS_8String16E");
int t630_am_is_uid_active(void) { return 1; }

int t630_am_uid_state(void)
    __asm__("_ZN7android15ActivityManager18getUidProcessStateEjRKNS_8String16E");
int t630_am_uid_state(void) { return 2; }

int t630_am_register_uids(void)
    __asm__("_ZN7android15ActivityManager26registerUidObserverForUidsERKNS_2spINS_12IUidObserverEEEiiRKNS_8String16EPKimRNS1_INS_7IBinderEEE");
int t630_am_register_uids(void) { return 0; }

int t630_am_unregister(void)
    __asm__("_ZN7android15ActivityManager21unregisterUidObserverERKNS_2spINS_12IUidObserverEEE");
int t630_am_unregister(void) { return 0; }

int t630_am_link_death(void)
    __asm__("_ZN7android15ActivityManager11linkToDeathERKNS_2spINS_7IBinder14DeathRecipientEEE");
int t630_am_link_death(void) { return 0; }

int t630_am_unlink_death(void)
    __asm__("_ZN7android15ActivityManager13unlinkToDeathERKNS_2spINS_7IBinder14DeathRecipientEEE");
int t630_am_unlink_death(void) { return 0; }

/* No Android sensor-privacy daemon is running.  Report that the optional
 * Android privacy-toggle feature is absent; GNOME's normal camera controls
 * remain unaffected. */
int t630_sp_supports_toggle(void)
    __asm__("_ZN7android20SensorPrivacyManager20supportsSensorToggleEii");
int t630_sp_supports_toggle(void) { return 0; }

int t630_sp_camera_enabled(void)
    __asm__("_ZN7android20SensorPrivacyManager22isCameraPrivacyEnabledENS_8String16E");
int t630_sp_camera_enabled(void) { return 0; }

int t630_sp_global_enabled(void)
    __asm__("_ZN7android20SensorPrivacyManager22isSensorPrivacyEnabledEv");
int t630_sp_global_enabled(void) { return 0; }

int t630_sp_toggle_enabled(void)
    __asm__("_ZN7android20SensorPrivacyManager28isToggleSensorPrivacyEnabledEi");
int t630_sp_toggle_enabled(void) { return 0; }

int t630_sp_toggle_state(void)
    __asm__("_ZN7android20SensorPrivacyManager27getToggleSensorPrivacyStateEii");
int t630_sp_toggle_state(void) { return 0; }

int t630_sp_add_listener(void)
    __asm__("_ZN7android20SensorPrivacyManager24addSensorPrivacyListenerERKNS_2spINS_8hardware22ISensorPrivacyListenerEEE");
int t630_sp_add_listener(void) { return 0; }

int t630_sp_remove_listener(void)
    __asm__("_ZN7android20SensorPrivacyManager27removeSensorPrivacyListenerERKNS_2spINS_8hardware22ISensorPrivacyListenerEEE");
int t630_sp_remove_listener(void) { return 0; }

int t630_sp_add_toggle_listener(void)
    __asm__("_ZN7android20SensorPrivacyManager30addToggleSensorPrivacyListenerERKNS_2spINS_8hardware22ISensorPrivacyListenerEEE");
int t630_sp_add_toggle_listener(void) { return 0; }

int t630_sp_remove_toggle_listener(void)
    __asm__("_ZN7android20SensorPrivacyManager33removeToggleSensorPrivacyListenerERKNS_2spINS_8hardware22ISensorPrivacyListenerEEE");
int t630_sp_remove_toggle_listener(void) { return 0; }

int t630_sp_link_death(void)
    __asm__("_ZN7android20SensorPrivacyManager11linkToDeathERKNS_2spINS_7IBinder14DeathRecipientEEE");
int t630_sp_link_death(void) { return 0; }

int t630_sp_unlink_death(void)
    __asm__("_ZN7android20SensorPrivacyManager13unlinkToDeathERKNS_2spINS_7IBinder14DeathRecipientEEE");
int t630_sp_unlink_death(void) { return 0; }
