cmake_minimum_required(VERSION 3.22.1)
project("whisper_jni_bridge" C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_C_STANDARD 11)

# ── whisper.cpp library (cloned into whisper.cpp/) ────────────────────
# Build only the core library; skip tests/examples.
set(WHISPER_BUILD_TESTS     OFF CACHE BOOL "" FORCE)
set(WHISPER_BUILD_EXAMPLES  OFF CACHE BOOL "" FORCE)
add_subdirectory(whisper.cpp)

# ── JNI bridge shared library ────────────────────────────────────────
add_library(whisper SHARED whisper_jni.c)

# Include whisper.h from the source tree
target_include_directories(whisper PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/whisper.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/whisper.cpp/include
)

# Link against the whisper.cpp static lib (built by the subdirectory)
target_link_libraries(whisper
    whisper.cpp    # the CMake target from whisper.cpp/CMakeLists.txt
    log            # Android log library
    m              # math
)
