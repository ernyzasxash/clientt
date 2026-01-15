#include "license_control.h"

bool g_bLicenseVerified = false;

void SetLicenseVerified(bool value) {
    g_bLicenseVerified = value;
}
