# BBK S6 (P20H130) Kernel Source

Qualcomm SM7150 (sdmmagpie / Snapdragon 730G) Android 内核源码，基于 CAF msm-4.14。

- **内核版本**: 4.14.190
- **CAF 基线**: `LA.UM.9.1.c25-01800-SMxxx0.QSSI12c26.0`
- **平台**: Qualcomm SM7150 / SM7150P (sdmmagpie / sdmmagpiep)
- **设备**: EEBBK S6 (P20H130)

## 功能状态（已在真机验证）

| 功能 | 状态 |
|------|------|
| 显示 (SDE/DSI) | ✅ 正常 |
| 存储 (UFS) | ✅ 正常 |
| 充电 | ✅ 正常 |
| USB (ADB) | ✅ 正常 |
| 触控 (FocalTech FT8203) | ✅ 正常 |
| 屏幕内核日志 (fbcon) | ✅ 已启用 |

## 快速编译

```bash
export ARCH=arm64
export CROSS_COMPILE=/path/to/binutils-2.27/bin/aarch64-linux-gnu-
export CC=/path/to/clang-11/bin/aarch64-linux-gnu-clang
export CLANG_TRIPLE=aarch64-linux-gnu-

# 用设备原始 config（从原内核 /proc/config.gz 提取）
cp config-gz-extracted .config
make olddefconfig

make -j$(nproc) Image REAL_CC=$CC CLANG_TRIPLE=aarch64-linux-gnu-
```

详细步骤见 [BUILDING.md](BUILDING.md)。

## 源码修改说明

本源码相对 CAF 基线包含以下修改：
1. **编译环境修复**（`scripts/`、`Makefile`）— 兼容现代 Ubuntu + clang-11
2. **haven 头文件**（`include/linux/haven/`）— 从 CAF 5.4 backport，供 FocalTech 驱动
3. **FocalTech 触摸驱动**（`drivers/input/touchscreen/focaltech_touch/`）— 官方版，支持 FT8201/FT8203
4. **drm_panel_notifier stub**（`drivers/gpu/drm/msm/`）— 兼容触摸驱动的 notifier 依赖

## 构建产物

- `arch/arm64/boot/Image` — 编译好的内核镜像（已含触控+fbcon）
- 刷入方式：见 [BUILDING.md](BUILDING.md) 或 TWRP 内 `dd` 到 recovery 分区
