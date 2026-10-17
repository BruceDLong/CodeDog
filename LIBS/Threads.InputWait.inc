// C++ thread-runtime boundary shared by desktop and Web Threads libraries.
// Every recursive acquisition spanning an input wait must use InputLock.
// Scopes are thread-local: a buffer can never release another reader's lock.
class CodeDogInputLock {
    friend class CodeDogInputPause;
    std::unique_lock<std::recursive_mutex> lock;
    CodeDogInputLock* previous;
    std::chrono::steady_clock::time_point lastYield = std::chrono::steady_clock::now();
    static CodeDogInputLock*& current() {
        static thread_local CodeDogInputLock* value = nullptr;
        return value;
    }
public:
    explicit CodeDogInputLock(std::recursive_mutex* mutex) : previous(current()) {
        if(mutex) lock = std::unique_lock<std::recursive_mutex>(*mutex);
        current() = this;
    }
    explicit CodeDogInputLock(std::recursive_mutex& mutex) : CodeDogInputLock(&mutex) {}
    CodeDogInputLock(const CodeDogInputLock&) = delete;
    CodeDogInputLock& operator=(const CodeDogInputLock&) = delete;
    ~CodeDogInputLock() { current() = previous; }
    static void yieldIfDue();
};

// Snapshot only locks currently owned by this thread. Nested callbacks may
// install new scopes while older scopes are suspended. Restore oldest first.
class CodeDogInputPause {
    std::vector<CodeDogInputLock*> scopes;
public:
    CodeDogInputPause() {
        for(auto* scope = CodeDogInputLock::current(); scope; scope = scope->previous)
            if(scope->lock.owns_lock()) scopes.push_back(scope);
        for(auto* scope : scopes) scope->lock.unlock();
    }
    CodeDogInputPause(const CodeDogInputPause&) = delete;
    CodeDogInputPause& operator=(const CodeDogInputPause&) = delete;
    ~CodeDogInputPause() {
        for(auto it = scopes.rbegin(); it != scopes.rend(); ++it) (*it)->lock.lock();
    }
};

inline void CodeDogInputLock::yieldIfDue() {
    auto* scope = current();
    if(!scope || !scope->lock.owns_lock()) return;
    auto now = std::chrono::steady_clock::now();
    if(now - scope->lastYield < std::chrono::milliseconds(5)) return;
    {
        CodeDogInputPause pause;
        // A short scheduling window avoids immediately retaking an unfair mutex.
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    scope->lastYield = std::chrono::steady_clock::now();
}

template<class Condition>
inline void codeDogWaitForInput(Condition& condition, std::unique_lock<std::mutex>& bufferLock) {
    {
        CodeDogInputPause pause;
        try {
            condition.wait(bufferLock);
        } catch(...) {
            // Never take the outer lock while holding the buffer lock, even
            // during unwinding. The caller's unique_lock remains consistent.
            if(bufferLock.owns_lock()) bufferLock.unlock();
            throw;
        }
        bufferLock.unlock();
    }
    bufferLock.lock();
    // The caller must recheck its predicate after both locks are restored.
}
