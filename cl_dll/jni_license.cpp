#include <jni.h>
#include "license_control.h"
#include "license_integrity.h"
#include <string>

extern "C" JNIEXPORT void JNICALL
Java_su_xash_cs16client_MainActivity_nativeSetLicenseVerified(JNIEnv *, jobject, jboolean verified) {
    SetLicenseVerified(verified);
}

extern "C" JNIEXPORT jstring JNICALL
Java_su_xash_cs16client_MainActivity_nativeGetCodeHash(JNIEnv *env, jobject) {
    std::string hash = CalculateCodeHash();
    return env->NewStringUTF(hash.c_str());
}
