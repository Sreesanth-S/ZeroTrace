// certificate_signer/certificate_signer.cpp
/**
 * ZeroTrace Certificate Signer
 * Uses OpenSSL to sign JSON certificates with RSA
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <openssl/rsa.h>
#include <openssl/pem.h>
#include <openssl/sha.h>
#include <openssl/bio.h>
#include <openssl/evp.h>
#include <openssl/buffer.h>

// Base64 encoding function
std::string base64_encode(const unsigned char* buffer, size_t length) {
    BIO *bio, *b64;
    BUF_MEM *bufferPtr;

    b64 = BIO_new(BIO_f_base64());
    bio = BIO_new(BIO_s_mem());
    bio = BIO_push(b64, bio);

    BIO_set_flags(bio, BIO_FLAGS_BASE64_NO_NL);
    BIO_write(bio, buffer, length);
    BIO_flush(bio);
    BIO_get_mem_ptr(bio, &bufferPtr);
    
    std::string result(bufferPtr->data, bufferPtr->length);
    
    BIO_free_all(bio);
    
    return result;
}

// Read file contents
std::string read_file(const std::string& filepath) {
    std::ifstream file(filepath, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filepath);
    }
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

// Write file contents
void write_file(const std::string& filepath, const std::string& content) {
    std::ofstream file(filepath, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot create file: " + filepath);
    }
    file << content;
}

// Sign JSON with RSA private key
std::string sign_json(const std::string& json_content, const std::string& private_key_path) {
    // Read private key
    FILE* key_file = fopen(private_key_path.c_str(), "r");
    if (!key_file) {
        throw std::runtime_error("Cannot open private key file");
    }
    
    EVP_PKEY* pkey = PEM_read_PrivateKey(key_file, nullptr, nullptr, nullptr);
    fclose(key_file);
    
    if (!pkey) {
        throw std::runtime_error("Cannot read private key");
    }
    
    // Create signing context
    EVP_MD_CTX* md_ctx = EVP_MD_CTX_new();
    if (!md_ctx) {
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Cannot create signing context");
    }
    
    // Initialize signing
    if (EVP_DigestSignInit(md_ctx, nullptr, EVP_sha256(), nullptr, pkey) != 1) {
        EVP_MD_CTX_free(md_ctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Cannot initialize signing");
    }
    
    // Update with data
    if (EVP_DigestSignUpdate(md_ctx, json_content.c_str(), json_content.length()) != 1) {
        EVP_MD_CTX_free(md_ctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Cannot update signing data");
    }
    
    // Get signature length
    size_t sig_len = 0;
    if (EVP_DigestSignFinal(md_ctx, nullptr, &sig_len) != 1) {
        EVP_MD_CTX_free(md_ctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Cannot get signature length");
    }
    
    // Get signature
    std::vector<unsigned char> signature(sig_len);
    if (EVP_DigestSignFinal(md_ctx, signature.data(), &sig_len) != 1) {
        EVP_MD_CTX_free(md_ctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Cannot finalize signature");
    }
    
    // Cleanup
    EVP_MD_CTX_free(md_ctx);
    EVP_PKEY_free(pkey);
    
    // Encode signature to Base64
    return base64_encode(signature.data(), sig_len);
}

int main(int argc, char* argv[]) {
    if (argc != 4) {
        std::cerr << "Usage: certificate_signer <json_file> <private_key> <output_file>" << std::endl;
        return 1;
    }
    
    std::string json_file = argv[1];
    std::string private_key_file = argv[2];
    std::string output_file = argv[3];
    
    try {
        // Read JSON content
        std::string json_content = read_file(json_file);
        
        // Sign the JSON
        std::string signature = sign_json(json_content, private_key_file);
        
        // Write signature to output file
        write_file(output_file, signature);
        
        std::cout << "Certificate signed successfully" << std::endl;
        std::cout << "Signature written to: " << output_file << std::endl;
        
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}