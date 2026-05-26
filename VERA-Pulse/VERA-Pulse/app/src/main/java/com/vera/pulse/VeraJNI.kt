package com.vera.pulse

object VeraJNI {
    external fun generateKeypair(): String
    external fun hpkeEncrypt(plaintext: String, publicKey: String): String
    external fun hpkeDecrypt(ciphertext: String): String
    external fun verifyAttestation(): Boolean
    
    companion object {
        init {
            System.loadLibrary("vera_core")
        }
    }
}
