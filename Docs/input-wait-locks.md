# Scoped locks across input waits

The C++ Threads runtime (desktop and Web) provides `InputLock`, `InputPause`,
`waitForInput` and `yieldInputLock`. They support consumers that protect a shared
model while parsing, but must let other threads use that model when input stops.
They do not depend on a particular parser or model type.

```text
// modelMutex is an existing recursive-mutex binding.
me InputLock: lock{modelMutex}
// Reads through strBuf release this lock only when more input is required.
```

`InputLock` owns one recursive-mutex acquisition for its lexical scope and
registers it on the current thread. Nested scopes are supported, including
multiple acquisitions of the same mutex. **Every acquisition held across an
input wait must use InputLock.** A raw lock or a separate `protect` acquisition
cannot be discovered or released by this runtime.

`strBuf.findInrBufWithPos` calls `waitForInput` only while its predicate requires
more bytes and the buffer is open. The wait suspends the calling thread's
registered input locks. On wake it releases the buffer mutex, restores the outer
locks in their original acquisition order, and then reacquires the buffer mutex.
The buffer loop rechecks its predicate. The same ordering applies on exceptions;
the caller's buffer lock is left unlocked during unwinding. Other buffer users
need no registration. Java, Kotlin and Swift retain their ordinary wait behavior;
scoped suspension is currently a C++ runtime facility.

Use a lexical `me InputPause: pause` around a host callback that must run outside
registered input locks. Ownership is restored when that scope exits, including
when the callback throws. Scopes temporarily installed by nested callbacks are
independent of the suspended scopes.

A consumer with buffered input should call `yieldInputLock()` only after publishing
a consistent unit of work. Once five milliseconds have elapsed, the helper
suspends registered locks and sleeps for one millisecond, giving competing
threads an opportunity to run before reacquisition. No pause occurs on every
character. This is cooperative scheduling, not a real-time deadline: a single
large token or computation can run until its next safe publication boundary.
