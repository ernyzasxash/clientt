#include "license_integrity.h"
#include <fstream>
#include <sstream>
#include <string>
#include <stdint.h>

static uint32_t simple_hash(const std::string& data) {
    uint32_t hash = 5381;
    for (char c : data) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash;
}

std::string CalculateCodeHash() {
    std::ifstream file("/proc/self/exe", std::ios::binary);
    if (!file) return "";
    std::ostringstream oss;
    oss << file.rdbuf();
    std::string data = oss.str();
    uint32_t hash = simple_hash(data);
    return std::to_string(hash);
}

bool CheckLicenseIntegrity(const std::string& expectedHash) {
    return CalculateCodeHash() == expectedHash;
}
