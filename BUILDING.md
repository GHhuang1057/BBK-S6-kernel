# 编译说明

## 前置工具链

编译这个 4.14 内核需要特定的旧工具链（新 GCC/Clang 无法编译）：

| 工具 | 版本 | 说明 |
|------|------|------|
| clang | 11.0.1 (AOSP 6443078) | 从 AOSP/LineageOS prebuilt 获取 |
| binutils | 2.27 (从源码编译) | 匹配原内核的 GNU ld 2.27 |
| gcc-aarch64 | 13.x (Ubuntu) | 仅用于 compiler-check，不编译内核 |

### 获取工具链

```bash
# 1. clang-11 (AOSP prebuilt, 从 crdroid 镜像)
wget https://codeload.github.com/crdroidandroid/android_prebuilts_clang_host_linux-x86_clang-6443078/tar.gz/refs/heads/10.0
tar -xzf clang-6443078.tar.gz
# 解压后目录: android_prebuilts_clang_host_linux-x86_clang-6443078-10.0/

# 2. binutils 2.27 (从源码编译，需要几分钟)
wget https://ftp.gnu.org/gnu/binutils/binutils-2.27.tar.gz
tar -xzf binutils-2.27.tar.gz
mkdir binutils-2.27-build && cd binutils-2.27-build
../binutils-2.27/configure --target=aarch64-linux-gnu --disable-nls --disable-werror --disable-gdb --disable-doc --prefix=$PWD/../binutils-2.27-install
make -j$(nproc)
make install

# 3. Ubuntu 交叉 gcc (compiler-check 用)
sudo apt-get install -y gcc-aarch64-linux-gnu
```

### 创建 clang 前缀链接

AOSP clang 需要 `aarch64-linux-gnu-` 前缀的工具链名：

```bash
CL=/path/to/android_prebuilts_clang_host_linux-x86_clang-6443078-10.0
cd $CL/bin
ln -sf clang-11 aarch64-linux-gnu-clang
ln -sf clang-11 aarch64-linux-gnu-clang++
ln -sf ld.lld aarch64-linux-gnu-ld
ln -sf llvm-ar aarch64-linux-gnu-ar
ln -sf llvm-nm aarch64-linux-gnu-nm
ln -sf llvm-objcopy aarch64-linux-gnu-objcopy
ln -sf llvm-objdump aarch64-linux-gnu-objdump
ln -sf llvm-strip aarch64-linux-gnu-strip
ln -sf llvm-readelf aarch64-linux-gnu-readelf
```

## 编译

```bash
cd kernel-source

export ARCH=arm64
export CROSS_COMPILE=/path/to/binutils-2.27-install/bin/aarch64-linux-gnu-
export PATH=/path/to/android_prebuilts_clang_host_linux-x86_clang-6443078-10.0/bin:$PATH

# 使用设备 config（config-gz-extracted 是从原内核 /proc/config.gz 提取的）
cp config-gz-extracted .config
make olddefconfig

# 编译
make -j$(nproc) Image \
  REAL_CC=/path/to/android_prebuilts_clang_host_linux-x86_clang-6443078-10.0/bin/aarch64-linux-gnu-clang \
  CLANG_TRIPLE=aarch64-linux-gnu-
```

产物：`arch/arm64/boot/Image`

## 刷入

```bash
# 设备进 TWRP 后（通过 ADB）
adb push arch/arm64/boot/Image /tmp/
# 内核需 gzip 压缩后原地替换进 boot/recovery 镜像
```

### 打包 recovery（原地替换法）

原 recovery.img 布局必须保持（ABL 依赖固定偏移）：

```bash
# 1. 压缩内核
gzip -n -9 -k -c arch/arm64/boot/Image > kernel.gz

# 2. 用 inplace_replace.py 原地替换（保持原布局/字段）
python3 tools/inplace_replace.py recovery.img kernel.gz recovery_new.img

# 3. 刷入
adb push recovery_new.img /sdcard/
adb shell dd if=/sdcard/recovery_new.img of=/dev/block/bootdevice/by-name/recovery bs=4096
```

## 已知源码修改

本源码已包含编译所需的全部修改（无需额外 patch）：

| 文件 | 修改 |
|------|------|
| `scripts/gcc-wrapper.py` | Python2→3 移植 |
| `scripts/dtc/Makefile` | `+ -fcommon` |
| `scripts/Makefile.build` | 空 built-in.o 改 `touch` |
| `include/linux/haven/` | 从 CAF 5.4 backport |
| `include/drm/drm_panel.h` | 补 drm_panel_notifier 定义 |
| `drivers/gpu/drm/msm/drm_panel_notifier_stub.c` | notifier stub |
| `drivers/input/touchscreen/focaltech_touch/` | 官方 FTS 驱动，支持 FT8201/FT8203 |
