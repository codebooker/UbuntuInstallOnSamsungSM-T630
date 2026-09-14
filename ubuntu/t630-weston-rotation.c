/* Runtime output rotation for the SM-T630's real Weston/DRM display. */
#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

#include <libweston/libweston.h>
#include <wayland-server-core.h>

#define ROTATION_FIFO "/run/t630-weston-rotation"
#define ROTATION_STATE "/run/t630-weston-rotation.state"

struct t630_rotation {
	struct weston_compositor *compositor;
	struct weston_output *output;
	struct wl_event_source *source;
	struct wl_listener destroy_listener;
	int fd;
};

static int
write_state(uint32_t transform)
{
	char value[2] = { (char)('0' + transform), '\n' };
	int fd = open(ROTATION_STATE, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC,
		      0644);
	ssize_t written;

	if (fd < 0)
		return -1;
	written = write(fd, value, sizeof value);
	close(fd);
	return written == (ssize_t)sizeof value ? 0 : -1;
}

static int
handle_rotation(int fd, uint32_t mask, void *data)
{
	struct t630_rotation *rotation = data;
	char buffer[64];
	ssize_t length;
	int transform = -1;

	if (!(mask & WL_EVENT_READABLE))
		return 0;
	while ((length = read(fd, buffer, sizeof buffer)) > 0) {
		ssize_t index;
		for (index = 0; index < length; index++) {
			if (buffer[index] >= '0' && buffer[index] <= '3')
				transform = buffer[index] - '0';
		}
	}
	if (length < 0 && errno != EAGAIN)
		return -1;
	if (transform < 0 || (uint32_t)transform == rotation->output->transform)
		return 0;

	weston_output_set_transform(rotation->output, (uint32_t)transform);
	/* set_transform updates geometry and clients, but unlike set_scale it does
	 * not tell shell plugins to reconfigure their fullscreen surfaces. */
	wl_signal_emit(&rotation->compositor->output_resized_signal,
		       rotation->output);
	weston_compositor_damage_all(rotation->compositor);
	weston_output_schedule_repaint(rotation->output);
	write_state((uint32_t)transform);
	return 0;
}

static void
destroy_rotation(struct wl_listener *listener, void *data)
{
	struct t630_rotation *rotation =
		wl_container_of(listener, rotation, destroy_listener);
	(void)data;

	if (rotation->source)
		wl_event_source_remove(rotation->source);
	if (rotation->fd >= 0)
		close(rotation->fd);
	unlink(ROTATION_FIFO);
	unlink(ROTATION_STATE);
	free(rotation);
}

WL_EXPORT int
wet_module_init(struct weston_compositor *compositor, int *argc, char *argv[])
{
	struct t630_rotation *rotation;
	struct wl_event_loop *loop;
	struct group *owner_group;
	struct stat info;
	(void)argc;
	(void)argv;

	rotation = calloc(1, sizeof *rotation);
	if (!rotation)
		return -1;
	rotation->fd = -1;
	rotation->compositor = compositor;
	rotation->output = weston_compositor_find_output_by_name(compositor, "DSI-1");
	if (!rotation->output)
		goto fail;

	if (lstat(ROTATION_FIFO, &info) == 0) {
		if (!S_ISFIFO(info.st_mode) || info.st_uid != 0)
			goto fail;
	} else if (errno != ENOENT || mkfifo(ROTATION_FIFO, 0620) < 0) {
		goto fail;
	}
	owner_group = getgrnam("t630-owner");
	if (!owner_group || chown(ROTATION_FIFO, 0, owner_group->gr_gid) < 0 ||
	    chmod(ROTATION_FIFO, 0620) < 0)
		goto fail;

	rotation->fd = open(ROTATION_FIFO, O_RDWR | O_NONBLOCK | O_CLOEXEC);
	if (rotation->fd < 0)
		goto fail;
	loop = wl_display_get_event_loop(compositor->wl_display);
	rotation->source = wl_event_loop_add_fd(
		loop, rotation->fd, WL_EVENT_READABLE, handle_rotation, rotation);
	if (!rotation->source)
		goto fail;

	rotation->destroy_listener.notify = destroy_rotation;
	wl_signal_add(&compositor->destroy_signal, &rotation->destroy_listener);
	write_state(rotation->output->transform);
	return 0;

fail:
	if (rotation->fd >= 0)
		close(rotation->fd);
	free(rotation);
	return -1;
}
