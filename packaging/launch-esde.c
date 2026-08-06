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
    if (snprintf(binary, sizeof(binary), "%s/es-de.bin", app_dir) >= (int)sizeof(binary) ||
        snprintf(library_path, sizeof(library_path), "%s/lib", app_dir) >= (int)sizeof(library_path)) {
        fputs("Application path is too long\n", stderr);
        return 1;
    }

    if (setenv("LD_LIBRARY_PATH", library_path, 1) < 0) {
        perror("setenv LD_LIBRARY_PATH");
        return 1;
    }

    const char *home = getenv("HOME");
    char fallback_home[PATH_MAX];
    if (home == NULL || home[0] == '\0' || access(home, W_OK) != 0) {
        if (snprintf(fallback_home, sizeof(fallback_home), "%s/data", app_dir) >=
            (int)sizeof(fallback_home)) {
            fputs("Home path is too long\n", stderr);
            return 1;
        }
        ensure_directory(fallback_home);
        setenv("HOME", fallback_home, 1);
        home = fallback_home;
    }

    char config_home[PATH_MAX];
    char cache_home[PATH_MAX];
    if (snprintf(config_home, sizeof(config_home), "%s/.config", home) < (int)sizeof(config_home)) {
        ensure_directory(config_home);
        setenv("XDG_CONFIG_HOME", config_home, 0);
    }
    if (snprintf(cache_home, sizeof(cache_home), "%s/.cache", home) < (int)sizeof(cache_home)) {
        ensure_directory(cache_home);
        setenv("XDG_CACHE_HOME", cache_home, 0);
    }

    chdir(app_dir);

    int log = open("/tmp/com.rf1705.esde.log", O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (log >= 0) {
        dup2(log, STDOUT_FILENO);
        dup2(log, STDERR_FILENO);
        close(log);
    }

    char **child_argv = calloc((size_t)argc + 3, sizeof(*child_argv));
    if (child_argv == NULL) {
        perror("calloc");
        return 1;
    }

    int destination = 0;
    child_argv[destination++] = binary;
    child_argv[destination++] = "--home";
    child_argv[destination++] = (char *)home;
    for (int source = 1; source < argc; ++source) {
        if (argv[source][0] == '{')
            continue;
        child_argv[destination++] = argv[source];
    }

    execv(binary, child_argv);
    dprintf(STDERR_FILENO, "Could not start ES-DE: %s\n", strerror(errno));
    return 1;
}
