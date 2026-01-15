#pragma once
#include <string>

bool CheckLicenseIntegrity(const std::string& expectedHash);
std::string CalculateCodeHash();
