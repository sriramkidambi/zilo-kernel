import os
import sys
import subprocess
import string
import random

bashfile=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
bashfile='/tmp/'+bashfile+'.sh'

f = open(bashfile, 'w')
s = """#!/bin/bash

# Telegram Config
TOKEN=$(/usr/bin/env python -c "import os; print(os.environ.get('TOKEN'))")
CHATID=$(/usr/bin/env python -c "import os; print(os.environ.get('CHATID'))")
CHANGELOG=$(/usr/bin/env python -c "import os; print(os.environ.get('CHANGELOG'))")
FORUMID=$(/usr/bin/env python -c "import os; print(os.environ.get('FORUMID'))")
BOT_MSG_URL="https://api.telegram.org/bot${TOKEN}/sendMessage"
BOT_BUILD_URL="https://api.telegram.org/bot${TOKEN}/sendDocument"
BOT_STICKER_URL="https://api.telegram.org/bot${TOKEN}/sendSticker"

# Build Machine details
cores=$(nproc --all)
os=$(cat /etc/issue)
time=$(TZ="Europe/Dublin" date "+%a %b %d %r")

# send msgs to tg
tg_post_msg() {
  curl -s -X POST "$BOT_MSG_URL" -d chat_id="$CHATID" \
    -d message_thread_id="${FORUMID}" \
    -d "disable_web_page_preview=true" \
    -d "parse_mode=html" \
    -d text="$1"
}

# send build to tg
tg_post_build()
{
	#Post MD5Checksum alongwith for easeness
	MD5CHECK=$(md5sum "$1" | cut -d' ' -f1)

	#Show the Checksum alongwith caption
	curl --progress-bar -F document=@"$1" "$BOT_BUILD_URL" \
	-F chat_id="$CHATID"  \
  -F message_thread_id="${FORUMID}" \
	-F "disable_web_page_preview=true" \
	-F "parse_mode=Markdown" \
	-F caption="$2 | *MD5 Checksum : *\`$MD5CHECK\`"
}

kernel_dir="${PWD}"
mkdir ${kernel_dir}/out
objdir="${kernel_dir}/out"
kf=$HOME/kf
builddir="${kernel_dir}/build"
ZIMAGE=$kernel_dir/out/arch/arm64/boot/Image.gz-dtb
psm_kernel_version=$(/usr/bin/env python -c "import os; print(os.environ.get('KernelVersion'))")
kernel_version=4.19.275
ksu_apk_name=KernelSU_v0.7.0_11326-release.apk
ksu_apk=https://github.com/tiann/KernelSU/releases/download/v0.7.0/KernelSU_v0.7.0_11326-release.apk
kernel_name="PSM-Kernel-${psm_kernel_version}-${kernel_version}-avicii"
zip_name="$kernel_name-$(date +"%d%m%Y-%H%M").zip"
export ARCH=arm64
export SUBARCH=arm64
export CONFIG_FILE="avicii_defconfig"
export BRAND_SHOW_FLAG=oneplus
export CCACHE=$(command -v ccache)
export PATH="$HOME/toolchains/neutron-clang/bin:${PATH}"
export CC="ccache clang"
export CLANG_TRIPLE="aarch64-linux-gnu-"
export CROSS_COMPILE="aarch64-linux-gnu-"
export CROSS_COMPILE_ARM32="arm-linux-gnueabi-"
export LLVM=1
export LLVM_IAS=1

# Sync submodule
git submodule init && git submodule update

#start off by sending a trigger msg
tg_post_msg "<b>PSM Kernel Build Triggered ⌛</b>%0A<b>==============================</b>%0A<b>Kernel : </b><code>${kernel_name}</code>%0A<b>Machine : </b><code>$os</code>%0A<b>Cores : </b><code>${cores}</code>%0A<b>Time : </b><code>${time}</code>"

# Colors
NC='\033[0m'
RED='\033[0;31m'
LRD='\033[1;31m'
LGR='\033[1;32m'

make_defconfig()
{
    START=$(date +"%s")
    tg_post_msg "PSM Kernel Build Triggered ⌛"
    echo -e ${LGR} "########### PSM Kernel Build Triggered ⌛ ############${NC}"
    tg_post_msg "Generating Defconfig"
    echo -e ${LGR} "########### Generating Defconfig ############${NC}"
    make -s ARCH=${ARCH} O=out ${CONFIG_FILE} -j$(nproc --all)
}

compile()
{
    tg_post_msg "Compiling kernel: ${kernel_name}"
    echo -e ${LGR} "######### Compiling kernel #########${NC}"
    make ARCH=${ARCH} O=out -j$(nproc --all) \
    2>&1 | tee error.log
}

completion() {
  cd ${objdir}
  COMPILED_IMAGE=arch/arm64/boot/Image.gz
  if [[ -f ${COMPILED_IMAGE} ]]; then
  
    tg_post_msg "<code>Image Generated✅</code>"
    echo -e ${LGR} "######### Image Generated ##########"

    mv -f $ZIMAGE $kf

    cd $kf
    find . -name "*.zip" -type f
    find . -name "*.zip" -type f -delete
    sed -i "s/version.string=/version.string=${psm_kernel_version}/g" anykernel.sh
    sed -i "s/Based on Linux Kernel KERNEL_VERSION_STRING/Based on Linux Kernel $kernel_version/g" META-INF/com/google/android/update-binary
    zip -r kf.zip *
    mv kf.zip $zip_name
    mv $kf/$zip_name $HOME/$zip_name
    rm -rf $kf
    curl -sL ${ksu_apk} > $HOME/${ksu_apk_name}
    tg_post_msg "<code>KernelSU Manager for this build Generated ✅</code>"
    echo -e ${LGR} "######### KernelSU Manager for this build Generated ##########"
    END=$(date +"%s")
    DIFF=$(($END - $START))
    BUILDTIME=$(echo $((${END} - ${START})) | awk '{print int ($1/3600)" Hours:"int(($1/60)%60)"Minutes:"int($1%60)" Seconds"}')
    tg_post_build "$HOME/$zip_name" "Build took : $((DIFF / 60)) minute(s) and $((DIFF % 60)) second(s)"
    tg_post_msg "<b>Changelog ($(date +%d-%m-%Y))</b>%0A<code>${CHANGELOG}</code>"
    tg_post_build $HOME/${ksu_apk_name} "KernelSU Manager for this build"
    tg_post_msg "<code>Compiled successfully✅</code>"
    curl --upload-file $HOME/$zip_name https://free.keep.sh
    echo
    echo -e ${LGR} "############################################"
    echo -e ${LGR} "######### Compilation succeeded :) ##########"
    echo -e ${LGR} "############################################${NC}"
    tg_post_msg "<code>Compilation succeeded :) ✅</code>"
  else
    tg_post_build "$kernel_dir/error.log" "$CHATID" "Debug Mode Logs"
    tg_post_msg "<code>Compilation failed❎</code>"
    echo -e ${RED} "############################################"
    echo -e ${RED} "##         Compilation failed :(          ##"
    echo -e ${RED} "############################################${NC}"
  fi
}
make_defconfig
if [ $? -eq 0 ]; then
    tg_post_msg "Defconfig generated successfully✅ "
    echo -e ${LGR} "### Defconfig generated successfully✅ #####"
fi
compile
completion
cd ${kernel_dir}/out
make arch=${ARCH} mrproper
make arch=${ARCH} clean
cd ${kernel_dir}
rm -r out
"""
f.write(s)
f.close()
os.chmod(bashfile, 0o755)
bashcmd=bashfile
for arg in sys.argv[1:]:
    bashcmd += ' '+arg
subprocess.call(bashcmd, shell=True)