#include "license_integrity.h"
#include <openssl/sha.h>
#include <fstream>
#include <sstream>

std::string CalculateCodeHash() {
    std::ifstream file("/proc/self/exe", std::ios::binary);
    if (!file) return "";
    std::ostringstream oss;
    oss << file.rdbuf();
    std::string data = oss.str();
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256((unsigned char*)data.c_str(), data.size(), hash);
    std::ostringstream hex;
    for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i)
        hex << std::hex << (int)hash[i];
    return hex.str();
}

bool CheckLicenseIntegrity(const std::string& expectedHash) {
    return CalculateCodeHash() == expectedHash;
}
