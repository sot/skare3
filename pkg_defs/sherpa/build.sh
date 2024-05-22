# if [ "$(uname -s)" == "Darwin" ]
# then
#   CONDA_BUILD_SYSROOT=/opt/MacOSX11.0.sdk
# fi

# #Apply patches
# git apply -v --whitespace=nowarn ${RECIPE_DIR}/patches/*.patch
# #Ignore the changes when setting the version
# # We only ignore files that were CHANGED by the patches, not any CREATED by the patches
# for CIAO_IGNORE in "setup.cfg conda_build_config.yaml"
# do
#   git update-index --assume-unchanged ${CIAO_IGNORE}
# done


$PYTHON -m pip install --prefix=$PREFIX -vv .
