import type { HashAlgorithm } from "@/types"

const HASH_LENGTHS: Record<HashAlgorithm, number> = {
  md5: 32,
  sha1: 40,
  sha256: 64,
}

export function normalizeExpectedHashInput(value: string): string {
  return value.trim().toLowerCase().replace(/^0x/i, "")
}

export function validateExpectedHashInput(
  algorithm: HashAlgorithm,
  value: string
): string | null {
  const normalized = normalizeExpectedHashInput(value)
  if (!normalized) {
    return "Enter an expected hash."
  }
  if (!/^[0-9a-f]+$/.test(normalized)) {
    return `Enter a valid ${algorithm.toUpperCase()} hash.`
  }
  if (normalized.length !== HASH_LENGTHS[algorithm]) {
    return `Enter a valid ${algorithm.toUpperCase()} hash.`
  }
  return null
}

export function getStoredAcquisitionHash(
  algorithm: HashAlgorithm,
  evidence: { md5: string; sha1: string; sha256: string }
): string {
  if (algorithm === "md5") return evidence.md5
  if (algorithm === "sha1") return evidence.sha1
  return evidence.sha256
}

export function isAcquisitionHashAvailable(
  algorithm: HashAlgorithm,
  evidence: { md5: string; sha1: string; sha256: string }
): boolean {
  return Boolean(getStoredAcquisitionHash(algorithm, evidence).trim())
}
