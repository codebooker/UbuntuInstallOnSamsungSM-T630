#include <errno.h>
#include <fcntl.h>
#include <linux/ioctl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

#define MAX_HEAP_NAME 32

struct ion_allocation_data {
    uint64_t len;
    uint32_t heap_id_mask;
    uint32_t flags;
    uint32_t fd;
    uint32_t unused;
};

struct ion_heap_data {
    char name[MAX_HEAP_NAME];
    uint32_t type;
    uint32_t heap_id;
    uint32_t reserved0;
    uint32_t reserved1;
    uint32_t reserved2;
};

struct ion_heap_query {
    uint32_t cnt;
    uint32_t reserved0;
    uint64_t heaps;
    uint32_t reserved1;
    uint32_t reserved2;
};

#define ION_IOC_MAGIC 'I'
#define ION_IOC_ALLOC _IOWR(ION_IOC_MAGIC, 0, struct ion_allocation_data)
#define ION_IOC_HEAP_QUERY _IOWR(ION_IOC_MAGIC, 8, struct ion_heap_query)

int main(void)
{
    int ion = open("/dev/ion", O_RDWR | O_CLOEXEC);
    struct ion_heap_query query = {0};
    struct ion_heap_data *heaps;

    if (ion < 0) {
        perror("open /dev/ion");
        return 1;
    }
    if (ioctl(ion, ION_IOC_HEAP_QUERY, &query) < 0) {
        perror("ION_IOC_HEAP_QUERY(count)");
        return 1;
    }
    heaps = calloc(query.cnt, sizeof(*heaps));
    if (!heaps)
        return 1;
    query.heaps = (uintptr_t)heaps;
    if (ioctl(ion, ION_IOC_HEAP_QUERY, &query) < 0) {
        perror("ION_IOC_HEAP_QUERY(data)");
        return 1;
    }

    for (uint32_t i = 0; i < query.cnt; i++) {
        struct ion_allocation_data alloc = {
            .len = 4096,
            .heap_id_mask = 1U << heaps[i].heap_id,
        };
        void *map;

        errno = 0;
        if (ioctl(ion, ION_IOC_ALLOC, &alloc) < 0) {
            printf("heap id=%u type=%u name=%s allocation rejected: %s\n",
                   heaps[i].heap_id, heaps[i].type, heaps[i].name,
                   strerror(errno));
            continue;
        }
        map = mmap(NULL, alloc.len, PROT_READ | PROT_WRITE, MAP_SHARED,
                   (int)alloc.fd, 0);
        printf("heap id=%u type=%u name=%s fd=%u mmap=%s\n",
               heaps[i].heap_id, heaps[i].type, heaps[i].name, alloc.fd,
               map == MAP_FAILED ? strerror(errno) : "ok");
        if (map != MAP_FAILED)
            munmap(map, alloc.len);
        close((int)alloc.fd);
    }
    free(heaps);
    close(ion);
    return 0;
}
