#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int ensure_directory(const char *path) {
    if (mkdir(path, 0755) == 0 || errno == EEXIST)
        return 0;
    return -1;
}

static int file_contains(const char *path, const char *needle) {
    FILE *file = fopen(path, "r");
    if (file == NULL)
        return 0;

    char buffer[4096];
    int found = 0;
    while (fgets(buffer, sizeof(buffer), file) != NULL) {
        if (strstr(buffer, needle) != NULL) {
            found = 1;
            break;
        }
    }
    fclose(file);
    return found;
}

static int copy_file(const char *source, const char *destination) {
    int input = open(source, O_RDONLY);
    if (input < 0)
        return -1;

    int output = open(destination, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (output < 0) {
        close(input);
        return -1;
    }

    char buffer[8192];
    ssize_t bytes;
    while ((bytes = read(input, buffer, sizeof(buffer))) > 0) {
        ssize_t offset = 0;
        while (offset < bytes) {
            ssize_t written = write(output, buffer + offset, (size_t)(bytes - offset));
            if (written < 0) {
                close(input);
                close(output);
                return -1;
            }
            offset += written;
        }
    }

    int saved_errno = errno;
    close(input);
    close(output);
    if (bytes < 0) {
        errno = saved_errno;
        return -1;
    }
    return 0;
}

int main(int argc, char **argv) {
    char executable[PATH_MAX];
    ssize_t length = readlink("/proc/self/exe", executable, sizeof(executable) - 1);
    if (length < 0) {
        perror("readlink");
        return 1;
    }
    executable[length] = '\0';

    char *separator = strrchr(executable, '/');
    if (separator == NULL) {
        fputs("Could not determine application directory\n", stderr);
        return 1;
    }
    *separator = '\0';
    const char *app_dir = executable;

    char binary[PATH_MAX];
    char library_path[PATH_MAX];
    if (snprintf(binary, sizeof(binary), "%s/emulationstation.bin", app_dir) >= (int)sizeof(binary) ||
        snprintf(library_path, sizeof(library_path), "%s/lib", app_dir) >= (int)sizeof(library_path)) {
        fputs("Application path is too long\n", stderr);
        return 1;
    }

    if (setenv("LD_LIBRARY_PATH", library_path, 1) < 0) {
        perror("setenv LD_LIBRARY_PATH");
        return 1;
    }

    /* SDL-webOS keeps shell keys for the TV shell by default. Claim Back and
       Home explicitly so SDL emits their webOS scancodes to EmulationStation.
       Home normally also opens the webOS ribbon; disable that shell action so
       the claimed Home key stays inside EmulationStation. */
    if (setenv("SDL_WEBOS_ACCESS_POLICY_KEYS_BACK", "true", 1) < 0) {
        perror("setenv SDL_WEBOS_ACCESS_POLICY_KEYS_BACK");
        return 1;
    }
    if (setenv("SDL_WEBOS_ACCESS_POLICY_KEYS_HOME", "true", 1) < 0) {
        perror("setenv SDL_WEBOS_ACCESS_POLICY_KEYS_HOME");
        return 1;
    }
    if (setenv("SDL_WEBOS_ACCESS_POLICY_RIBBON", "false", 1) < 0) {
        perror("setenv SDL_WEBOS_ACCESS_POLICY_RIBBON");
        return 1;
    }

    const char *home = getenv("HOME");
    char fallback_home[PATH_MAX];
    if (home == NULL || home[0] == '\0' || access(home, W_OK) != 0) {
        if (snprintf(fallback_home, sizeof(fallback_home), "%s/data", app_dir) >= (int)sizeof(fallback_home)) {
            fputs("Home path is too long\n", stderr);
            return 1;
        }
        if (ensure_directory(fallback_home) < 0) {
            perror("mkdir fallback HOME");
            return 1;
        }
        setenv("HOME", fallback_home, 1);
        home = fallback_home;
    }

    char config_dir[PATH_MAX];
    char config_file[PATH_MAX];
    char default_config[PATH_MAX];
    if (snprintf(config_dir, sizeof(config_dir), "%s/.emulationstation", home) >= (int)sizeof(config_dir) ||
        snprintf(config_file, sizeof(config_file), "%s/es_systems.cfg", config_dir) >= (int)sizeof(config_file) ||
        snprintf(default_config, sizeof(default_config), "%s/default-es_systems.cfg", app_dir) >= (int)sizeof(default_config)) {
        fputs("Configuration path is too long\n", stderr);
        return 1;
    }

    if (ensure_directory(config_dir) < 0) {
        perror("mkdir EmulationStation config");
        return 1;
    }

    /* RetroPie writes its desktop NES example after a missing config. Replace
       only that known generated example; never overwrite a user configuration. */
    if (access(config_file, F_OK) != 0 || file_contains(config_file, "<path>~/roms/nes</path>")) {
        if (copy_file(default_config, config_file) < 0) {
            perror("copy default es_systems.cfg");
            return 1;
        }
    }

    chdir(app_dir);

    int log = open("/tmp/com.rf1705.emulationstation.log", O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (log >= 0) {
        dup2(log, STDOUT_FILENO);
        dup2(log, STDERR_FILENO);
        close(log);
    }

    char **child_argv = calloc((size_t)argc + 6, sizeof(*child_argv));
    if (child_argv == NULL) {
        perror("calloc");
        return 1;
    }

    int destination = 0;
    child_argv[destination++] = binary;
    child_argv[destination++] = "--home";
    child_argv[destination++] = (char *)home;
    child_argv[destination++] = "--no-exit";
    child_argv[destination++] = "--no-confirm-quit";
    for (int source = 1; source < argc; ++source) {
        if (argv[source][0] == '{')
            continue;
        child_argv[destination++] = argv[source];
    }

    execv(binary, child_argv);
    dprintf(STDERR_FILENO, "Could not start EmulationStation: %s\n", strerror(errno));
    return 1;
}
