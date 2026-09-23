#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    setbuf(stdout, NULL);

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return EXIT_FAILURE;
    }

    if (pid == 0) {
        printf("child: running\n");
        printf("child: exiting with status 7\n");
        return 7;
    }

    printf("parent: waiting for child-pid=%ld\n", (long)pid);
    int status = 0;
    pid_t reaped = waitpid(pid, &status, 0);
    if (reaped < 0) {
        perror("waitpid");
        return EXIT_FAILURE;
    }

    printf("parent: waitpid returned child-pid=%ld\n", (long)reaped);
    printf("parent: child exited normally=%s status=%d\n",
           WIFEXITED(status) ? "yes" : "no", WEXITSTATUS(status));
    return EXIT_SUCCESS;
}
