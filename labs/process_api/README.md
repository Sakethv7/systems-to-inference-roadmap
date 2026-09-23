# Layer 1 lab: `fork()`, `wait()`, and `exec()`

This is a small process-API lab. It does not update the learning app or mark
anything complete.

## Build

```sh
cd labs/process_api
cc -Wall -Wextra -std=c17 fork_basic.c -o fork_basic
cc -Wall -Wextra -std=c17 fork_wait.c -o fork_wait
cc -Wall -Wextra -std=c17 fork_exec.c -o fork_exec
cc -Wall -Wextra -std=c17 exec_target.c -o exec_target
```

## Learning protocol

Before each run, write your predicted output in `prediction_log.md`. Then run
exactly that program, paste the observation, and explain which prediction was
wrong or incomplete. Repeat a program several times when it contains an
ordering race. A repeated order is evidence about this machine and workload,
not a guarantee from `fork()`.

Run from this directory:

```sh
./fork_basic
./fork_wait
./fork_exec
```

The programs use unbuffered stdout so the lesson is about process scheduling,
not duplicated stdio buffers inherited across `fork()`.
