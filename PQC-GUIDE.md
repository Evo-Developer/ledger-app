# Post-Quantum Cryptography (PQC) Implementation Guide

## Overview

This application is **PQC-ready** and designed to easily migrate to Post-Quantum Cryptography when needed. Currently, it uses quantum-resistant password hashing (Argon2id) and has a modular architecture that allows seamless upgrade to NIST-approved PQC algorithms.

## Current Status: PQC-Ready ✅

### Already Quantum-Resistant

1. **Password Hashing - Argon2id**
   - ✅ Memory-hard function
   - ✅ Not significantly affected by Grover's algorithm
   - ✅ Quantum computers only provide quadratic speedup (~2x, not exponential)
   - ✅ By increasing memory cost, we maintain security against quantum attacks

### Why Current Implementation is Secure

**Quantum Threat Timeline:**
- Large-scale quantum computers: 10-20+ years away
- Current implementation: Secure for foreseeable future
- Argon2id: Designed to resist quantum speedups
- Easy upgrade path: When needed, transition is straightforward

## PQC Migration Roadmap

### Phase 1: Current State (Production-Ready)
```
✅ Argon2id for password hashing
✅ HMAC-SHA256 for JWT signing  
✅ AES-256 for encryption (when implemented)
✅ Modular cryptographic design
✅ Security best practices
```

**Security Level:** Quantum-resistant for password hashing, classical security for signatures.

### Phase 2: Hybrid Approach (Recommended First Step)
```
Combine classical + PQC algorithms for defense-in-depth
Timeline: When quantum computers reach ~100 logical qubits

Changes needed:
- JWT: Use RSA-2048 + Dilithium3
- Key Exchange: ECDH + Kyber768
- Keep Argon2id (already quantum-resistant)
```

**Benefit:** Protects against both classical and quantum attacks.

### Phase 3: Full PQC (Future)
```
Replace all classical algorithms with PQC
Timeline: When NIST standards are widely adopted (5-10 years)

Changes:
- Signatures: Dilithium3 or Falcon-512
- Key Exchange: Kyber768 or Kyber1024
- Keep Argon2id (still best for passwords)
```

## Installing PQC Libraries (Optional)

### Prerequisites

**System Dependencies (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y \
    cmake \
    ninja-build \
    libssl-dev \
    gcc \
    g++ \
    git
```

**System Dependencies (macOS):**
```bash
brew install cmake ninja openssl
```

### Installing liboqs

**1. Install liboqs system library:**
```bash
# Clone repository
git clone -b main https://github.com/open-quantum-safe/liboqs.git
cd liboqs

# Build
mkdir build && cd build
cmake -GNinja \
    -DCMAKE_INSTALL_PREFIX=/usr/local \
    -DBUILD_SHARED_LIBS=ON \
    ..

# Install
ninja
sudo ninja install

# Update library cache (Linux only)
sudo ldconfig
```

**2. Install Python bindings:**
```bash
pip install liboqs-python==0.14.1
```

**3. Verify installation:**
```python
import oqs

print("Signature algorithms:", oqs.get_enabled_sig_mechanisms())
print("KEM algorithms:", oqs.get_enabled_kem_mechanisms())
```

## NIST-Approved PQC Algorithms

### For Digital Signatures

**Dilithium (Recommended)**
- **Use case:** JWT signing, API authentication
- **Security levels:** 
  - Dilithium2 (NIST Level 2) - ~128-bit security
  - Dilithium3 (NIST Level 3) - ~192-bit security  
  - Dilithium5 (NIST Level 5) - ~256-bit security
- **Performance:** Fast signing and verification
- **Status:** NIST approved for standardization

**Falcon**
- **Use case:** Resource-constrained environments
- **Security levels:**
  - Falcon-512 (NIST Level 1)
  - Falcon-1024 (NIST Level 5)
- **Performance:** Smaller signatures than Dilithium
- **Status:** NIST approved for standardization

**SPHINCS+**
- **Use case:** Long-term security, low signing frequency
- **Security:** Hash-based (extremely conservative)
- **Performance:** Slow signing, fast verification
- **Status:** NIST approved for standardization

### For Key Encapsulation (KEM)

**CRYSTALS-KYBER (Recommended)**
- **Use case:** TLS, secure communications
- **Security levels:**
  - Kyber512 (NIST Level 1)
  - Kyber768 (NIST Level 3) - **Recommended**
  - Kyber1024 (NIST Level 5)
- **Performance:** Fast encapsulation/decapsulation
- **Status:** NIST selected for standardization

## Implementation Examples

### Example 1: PQC JWT Signing (When Ready)

```python
# File: pqc_auth.py (Future implementation)
import oqs
import json
import base64
from datetime import datetime, timedelta

class PQCJWTHandler:
    """
    Post-Quantum JWT handler using Dilithium
    """
    
    def __init__(self):
        # Use Dilithium3 for signing
        self.sig_algorithm = "Dilithium3"
        self.signer = oqs.Signature(self.sig_algorithm)
        
        # Generate key pair (do this once, store securely)
        self.public_key = self.signer.generate_keypair()
        self.private_key = self.signer.export_secret_key()
    
    def create_token(self, data: dict) -> str:
        """Create PQC-signed JWT"""
        # Create header
        header = {
            "alg": "Dilithium3",
            "typ": "JWT"
        }
        
        # Create payload
        payload = data.copy()
        payload.update({
            "exp": (datetime.utcnow() + timedelta(minutes=30)).timestamp(),
            "iat": datetime.utcnow().timestamp()
        })
        
        # Encode header and payload
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip('=')
        
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')
        
        # Create message to sign
        message = f"{header_b64}.{payload_b64}"
        
        # Sign with Dilithium
        signature = self.signer.sign(message.encode())
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        # Return JWT
        return f"{message}.{signature_b64}"
    
    def verify_token(self, token: str) -> dict:
        """Verify PQC-signed JWT"""
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        header_b64, payload_b64, signature_b64 = parts
        
        # Reconstruct message
        message = f"{header_b64}.{payload_b64}"
        
        # Decode signature
        signature = base64.urlsafe_b64decode(
            signature_b64 + '=' * (4 - len(signature_b64) % 4)
        )
        
        # Verify signature
        is_valid = self.signer.verify(
            message.encode(),
            signature,
            self.public_key
        )
        
        if not is_valid:
            raise ValueError("Invalid signature")
        
        # Decode and return payload
        payload_json = base64.urlsafe_b64decode(
            payload_b64 + '=' * (4 - len(payload_b64) % 4)
        )
        
        return json.loads(payload_json)
```

### Example 2: Hybrid Classical + PQC

```python
# File: hybrid_auth.py (Recommended approach)
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
import oqs

class HybridSigner:
    """
    Hybrid signing: RSA + Dilithium
    Provides security against both classical and quantum attacks
    """
    
    def __init__(self):
        # Classical: RSA
        self.rsa_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # PQC: Dilithium
        self.pqc_signer = oqs.Signature("Dilithium3")
        self.pqc_public_key = self.pqc_signer.generate_keypair()
    
    def sign(self, message: bytes) -> tuple:
        """Sign with both RSA and Dilithium"""
        # RSA signature
        rsa_sig = self.rsa_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Dilithium signature
        pqc_sig = self.pqc_signer.sign(message)
        
        return (rsa_sig, pqc_sig)
    
    def verify(self, message: bytes, signatures: tuple) -> bool:
        """Verify both signatures"""
        rsa_sig, pqc_sig = signatures
        
        # Both must be valid
        try:
            # Verify RSA
            self.rsa_key.public_key().verify(
                rsa_sig,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Verify Dilithium
            is_pqc_valid = self.pqc_signer.verify(
                message,
                pqc_sig,
                self.pqc_public_key
            )
            
            return is_pqc_valid
            
        except Exception:
            return False
```

## Migration Checklist

### When to Migrate

- [ ] NIST finalizes PQC standards (Expected: 2024-2025)
- [ ] Libraries are production-ready
- [ ] Performance is acceptable for your use case
- [ ] You have quantum threat timeline (10+ years usually safe)

### Migration Steps

1. **Preparation**
   ```bash
   # Install PQC libraries
   pip install -r requirements-pqc.txt
   
   # Run tests
   python -m pytest tests/test_pqc.py
   ```

2. **Hybrid Deployment (Recommended)**
   ```python
   # Update auth.py to use hybrid signing
   from hybrid_auth import HybridSigner
   
   # Use both classical and PQC
   signer = HybridSigner()
   ```

3. **Testing**
   - Test with small subset of users
   - Monitor performance
   - Verify compatibility

4. **Rollout**
   - Deploy to staging
   - Performance testing
   - Gradual production rollout

5. **Full Migration**
   - After 6-12 months of hybrid mode
   - Remove classical algorithms
   - Pure PQC implementation

## Performance Considerations

### Current (Argon2id + RSA/HMAC)
- Password hashing: ~50ms
- JWT signing: <1ms
- JWT verification: <1ms

### With PQC (Dilithium3)
- Password hashing: ~50ms (same)
- JWT signing: ~2-5ms
- JWT verification: ~1-2ms
- Signature size: ~3KB (vs ~256 bytes for RSA)

### Optimization Tips
- Cache public keys
- Use Dilithium2 for lower security needs
- Consider Falcon for size-constrained environments
- Use hardware acceleration when available

## Compliance & Standards

### NIST PQC Standardization
- **Round 4:** Completed
- **Draft Standards:** Expected 2024
- **Final Standards:** 2024-2025
- **Widespread Adoption:** 2025-2030

### Recommended Timeline
- **Now:** Use Argon2id (quantum-resistant for passwords)
- **2024-2025:** Implement hybrid approach
- **2025-2027:** Test and validate PQC
- **2028+:** Full PQC migration

## Resources

- NIST PQC Project: https://csrc.nist.gov/projects/post-quantum-cryptography
- Open Quantum Safe: https://openquantumsafe.org/
- liboqs Documentation: https://github.com/open-quantum-safe/liboqs
- CRYSTALS-Dilithium: https://pq-crystals.org/dilithium/
- CRYSTALS-KYBER: https://pq-crystals.org/kyber/

## FAQ

**Q: Do I need PQC right now?**
A: No. Current implementation with Argon2id is secure. Large-scale quantum computers are 10-20+ years away.

**Q: Is Argon2id quantum-resistant?**
A: Yes. Memory-hard functions like Argon2id are not significantly affected by quantum computers.

**Q: When should I migrate to PQC?**
A: When NIST finalizes standards AND quantum computers become a realistic threat (monitor NIST timeline).

**Q: What's the performance impact?**
A: PQC signatures are larger and slightly slower, but acceptable for most applications.

**Q: Can I use hybrid mode permanently?**
A: Yes. Hybrid mode provides defense-in-depth and is recommended during transition period.

---

**Status:** PQC-Ready  
**Current Security:** Quantum-resistant password hashing  
**Recommended Action:** Monitor NIST standardization, prepare for hybrid deployment in 2024-2025
