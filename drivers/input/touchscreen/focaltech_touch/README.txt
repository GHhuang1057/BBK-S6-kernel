# linux/drivers/input/touchscreen/focaltech_touch

本驱动适用于FocalTech(敦泰) FT8201及FT8201AB中心触摸控制ic

取自Firefly RK3399开发板公开源码，额外添加了部分FT8201(AB)相关驱动支持，取消Firefly Panel ID检测，若欲恢复可以使用带有bakup后缀名称的驱动文件，不加载特殊屏幕固件，若在不适用的屏幕上面加载固件将可能导致触摸控制暂时失灵，同时可能造成不可预料的后果。

适用范围(仅为估量，出现问题请自行移植): Linux 3.18~4.19

使用方法:

    在linux/drivers/input/touchscreen/Kconfig中添加:
    
source "drivers/input/touchscreen/focaltech_touch/Kconfig"
    
    在linux/drivers/input/touchscreen/Makefile中添加:
    
obj-$(CONFIG_TOUCHSCREEN_FTS)		+= focaltech_touch/

    随后，复制本目录的所有内容到drivers/input/touchscreen/focaltech_touch目录

    若您想要编译此驱动请在您的要编译的平台特定config中添加:
    
CONFIG_TOUCHSCREEN_FTS=y
CONFIG_TOUCHSCREEN_FTS_DIRECTORY="focaltech_touch"
CONFIG_OF_TOUCHSCREEN=y

本驱动在EEBBK S5测试可用
By XiKoTaSu