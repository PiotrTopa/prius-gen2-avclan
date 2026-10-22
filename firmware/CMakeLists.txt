cmake_minimum_required(VERSION 3.13)

# Target board: Waveshare RP2040-Zero by default; the RP2350-Zero (same
# pinout) builds with -DPICO_BOARD=waveshare_rp2350_zero.
set(PICO_BOARD waveshare_rp2040_zero CACHE STRING "Board type")

include(pico_sdk_import.cmake)

project(avclan_rp2040 C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(avclan_rp2040
    src/main.c
    src/commands.c
    src/out.c
    src/usb_cdc.c
    src/usb_descriptors.c
    src/json_util.c
    src/avclan_codec.c
    src/avclan.c
    src/led.c
)

pico_generate_pio_header(avclan_rp2040 ${CMAKE_CURRENT_LIST_DIR}/src/avclan.pio)

target_include_directories(avclan_rp2040 PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src)

target_compile_options(avclan_rp2040 PRIVATE -Wall -Wextra -Wno-unused-parameter)

# Core-0 stack: 4 KB (fills SCRATCH_Y; the SDK default is 2 KB). All big line
# buffers are static, so this leaves ample headroom for printf/TinyUSB.
target_compile_definitions(avclan_rp2040 PRIVATE PICO_STACK_SIZE=0x1000)

target_link_libraries(avclan_rp2040
    pico_stdlib
    pico_unique_id
    pico_bootrom
    hardware_pio
    hardware_dma
    hardware_irq
    hardware_gpio
    hardware_clocks
    hardware_watchdog
    tinyusb_device
)

# The USB port is the protocol channel, not a console.
pico_enable_stdio_usb(avclan_rp2040 0)
pico_enable_stdio_uart(avclan_rp2040 0)

pico_set_program_name(avclan_rp2040 "avclan_rp2040")
pico_set_program_description(avclan_rp2040 "AVC-LAN (IEBus) transceiver, USB NDJSON - carved out of a multi-bus gateway firmware")
pico_set_program_version(avclan_rp2040 "3.2.0")

pico_add_extra_outputs(avclan_rp2040)
