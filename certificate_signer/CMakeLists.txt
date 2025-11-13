# certificate_signer/CMakeLists.txt
cmake_minimum_required(VERSION 3.15)
project(certificate_signer)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find OpenSSL
find_package(OpenSSL REQUIRED)

# Add executable
add_executable(certificate_signer certificate_signer.cpp)

# Link OpenSSL
target_link_libraries(certificate_signer OpenSSL::SSL OpenSSL::Crypto)

# Installation
install(TARGETS certificate_signer DESTINATION bin)

# For Windows, we might want to copy OpenSSL DLLs
if(WIN32)
    # Copy OpenSSL DLLs to build directory
    add_custom_command(TARGET certificate_signer POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<TARGET_FILE:OpenSSL::SSL>
        $<TARGET_FILE_DIR:certificate_signer>
    )
    add_custom_command(TARGET certificate_signer POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<TARGET_FILE:OpenSSL::Crypto>
        $<TARGET_FILE_DIR:certificate_signer>
    )
endif()