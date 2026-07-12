# Password-Based Authentication Security Assessment

---

## 1. Brute-Force Attacks

### Attack Mechanism

Brute-force attacks systematically attempt every possible character combination until the correct credential is found. Two variants exist:

- **Online brute-force**: Attacker sends login attempts to the live application. Constrained by network latency, server processing time, and (ideally) rate limiting. Realistic speeds are tens to low hundreds of attempts per second on unprotected endpoints, dropping to a few attempts per hour on rate-limited services.

- **Offline brute-force**: Attacker has obtained a password hash database (via breach, backup exposure, etc.) and cracks hashes locally at high speed. This is the far more dangerous scenario — the only ceiling is hardware and the hashing algorithm's work factor.

### Modern GPU Credential Cracking Speeds

| Algorithm | NVIDIA RTX 4090 (approx. hashes/sec) |
|---|---|
| MD5 | ~164,000,000,000 |
| SHA1 | ~53,000,000,000 |
| NTLM | ~313,000,000,000 |
| SHA256 (unsalted) | ~23,000,000,000 |
| bcrypt (cost 5) | ~105,000 |
| bcrypt (cost 12) | ~250 |
| PBKDF2-SHA256 (100k iter) | ~1,400 |
| Argon2id (default params) | ~30 |

A 12-character truly random password (95-character alphabet) has ~5.4 x 10^23 possible combinations. At 164 GH/s (MD5), that still requires ~105,000 years. An 8-character password has ~6.6 x 10^15 combinations — cracked at MD5 speed in ~11 hours, or an 8-char NTLM hash in ~6 seconds. **Length is the dominant factor**, not just algorithm choice.

### Severity: **Critical** (offline), **High** (online unmitigated)

Offline cracking is critical because a single database breach exposes all users whose passwords are below the "uncrackable" entropy threshold. Most users do not use 12+ character random passwords.

### Mitigations (ranked by effectiveness)

1. **Adaptive hashing algorithms** (Argon2id > bcrypt > PBKDF2) with high work factors — makes each hash guess computationally expensive
2. **Account lockout after N consecutive failures** (temporary, e.g. exponential backoff or 15-min lockout after 5 failures)
3. **IP-based rate limiting** with sliding windows, not fixed-interval counters
4. **CAPTCHA / proof-of-work challenges** after repeated failures
5. **Enforce minimum password length of 12+ characters** (NIST SP 800-63B recommends 8 minimum, 64 maximum)
6. **Monitor for distributed attacks** across many IPs targeting many accounts (credential spraying pattern)
7. **Breached password detection** at registration and password change time to reject known-weak passwords

### Statistics

- Verizon 2024 DBIR: 31% of breaches involved use of stolen credentials
- Microsoft studies: 99.9% of compromised accounts didn't have MFA enabled
- A 2023 Hive Systems study showed an 8-character complex password could be cracked in 5 minutes (MD5) but 2 billion years with bcrypt cost 12

---

## 2. Credential Stuffing

### Attack Mechanism

Credential stuffing exploits the fact that users reuse passwords across services. Attackers take username/password pairs exposed in one breach and automatically test them against unrelated services using bots, distributed IPs, and residential proxy networks. Unlike brute-force (trying many passwords against one account), credential stuffing tries one known-good credential pair against many services.

Attackers use tools like Sentry MBA, Snipr, or OpenBullet with proxy lists containing millions of residential IPs. Configuration files ("configs") for specific websites handle CSRF token extraction, session cookie management, and success/failure fingerprinting.

### Severity: **Critical**

Credential stuffing is the most common attack vector against consumer-facing web applications. Akamai reported 193 billion credential stuffing attacks in 2023 alone. The attack has near-zero cost (password lists are freely available from breaches like Collection #1 which contained 773 million unique credentials), and success rates of 0.1-2% produce thousands of account takeovers at scale.

### Mitigations (ranked by effectiveness)

1. **Multi-factor authentication (MFA)** — single most effective control; even a compromised password can't be used without the second factor
2. **Breached password detection** — check passwords (via k-anonymity model, e.g. NIST 800-63B) against known breach corpuses at registration and login
3. **Bot detection and fingerprinting** — browser fingerprinting (Canvas, WebGL, font enumeration), behavioral analytics (mouse movement, keystroke dynamics), TLS fingerprinting (JA3/JA4)
4. **Rate limiting by IP + account** — separate rate limits per target account AND per source IP
5. **CAPTCHA on high-risk logins** (new device, geo-anomaly, Tor exit node)
6. **Credential hashing on the client side** (slow hashing in browser before transmission) as an additional friction layer
7. **Passwordless authentication** (WebAuthn/passkeys) eliminates the credential reuse vector entirely

### Statistics

- Akamai: 193 billion credential stuffing attempts in 2023
- Shape Security (F5): 80-90% of e-commerce login traffic is credential stuffing
- Verizon DBIR 2024: use of stolen credentials present in 31% of all breaches
- 0.1-2% success rate still yields massive account takeovers at scale

---

## 3. Rainbow Tables

### Attack Mechanism

A rainbow table is a time-memory trade-off to crack password hashes. Instead of computing each hash on demand:

1. **Precomputation phase**: A chain reduction function repeatedly alternates between hashing and reducing a password candidate, storing only the start and end of each chain. A rainbow table for an 8-character alphanumeric MD5 hash occupies roughly 400 GB.

2. **Lookup phase**: Given a target hash, the attacker applies the chain reduction function repeatedly. If any intermediate value matches an endpoint stored in the table, the attacker can reconstruct the chain and recover the original password.

Rainbow tables are algorithm-specific (the chain construction depends on the hash function), character-set-specific, and length-bounded. An MD5 table for 1-8 chars [a-z0-9] works against any MD5 hash meeting those constraints.

### Why Salting Defeats Rainbow Tables

A **salt** is a cryptographically random value prepended or appended to the password before hashing. If salt length is 16 bytes (128 bits), then each password effectively has 2^128 possible hash variations. A rainbow table would need to be precomputed for every possible salt value — that's 340 undecillion tables, making the attack computationally infeasible. A unique salt per user also defeats the "shared table" advantage: even if two users have the same password, their hashes differ.

### Severity: **Medium** (modern systems w/ proper hashing), **Critical** (legacy unsalted hashes)

Modern frameworks (Django, Rails, Laravel, Spring Security) salt by default. However, legacy systems, embedded devices, IoT firmware, and poorly implemented custom authentication still use unsalted MD5/SHA1/SHA256. Once those hashes leak, rainbow table lookup is near-instantaneous.

### Mitigations (ranked by effectiveness)

1. **Per-user cryptographic salt** — minimum 128 bits, generated via CSPRNG, unique per password (re-salt on password change)
2. **Pepper** — a server-side secret (stored in HSM, environment variable, or key management service) added to password+salt, protecting against database-only breaches
3. **Adaptive hashing** (Argon2id, bcrypt, scrypt) — these incorporate salts natively and are computationally expensive
4. **Password length enforcement** — rainbow tables grow exponentially with password length; tables for 12+ char passwords are impractical

### Statistics

- Cost to generate a full rainbow table for 1-9 char MD5 [a-z0-9]: approximately $5,000 in GPU compute time
- Same for 1-12 chars: effectively impossible ($billions)
- Project RainbowCrack and FreeRainbowTables.com (defunct) once provided free downloads covering most common hash types for short passwords

---

## 4. Phishing

### Attack Mechanism

Phishing encompasses a spectrum of techniques designed to trick users into revealing credentials:

#### 4a. Spear Phishing
Targeted emails crafted for specific individuals or organizations. Attackers research the target via LinkedIn, corporate websites, and previous breach data. Emails appear to come from known contacts, use organization-specific jargon, and reference real projects or events. Success rates are 10-30x higher than generic phishing.

#### 4b. Clone Pages
Replicas of legitimate login pages (Office 365, Google Workspace, banking portals) hosted on lookalike domains (e.g. `rnicrosoft.com` with Cyrillic 'i', `accounts-gooqle.com`). Modern toolkits like Evilginx and Modlishka clone the real site in real-time by proxying traffic between the victim and the legitimate service.

#### 4c. Real-Time Phishing Proxies (AiTM — Adversary-in-the-Middle)
The most dangerous variant. Tools like Evilginx2, Modlishka, and Muraena sit between the victim and the legitimate service, acting as a reverse proxy. When the victim completes authentication (including MFA), the proxy steals the session cookie. This bypasses MFA because the attacker captures the fully authenticated session, not just the password. This is how the 2022 Uber breach, the 2022 Twilio breach, and the 2022-2023 Okta compromises were executed.

#### 4d. MFA Bypass Phishing
- **MFA fatigue / push bombing**: Attacker triggers repeated MFA push notifications until the victim accepts to stop the annoyance (Lapsus$ group's Uber breach).
- **SIM swapping**: Social engineering mobile carriers to transfer the victim's phone number to the attacker's SIM, intercepting SMS-based MFA codes.
- **OTP interception tools**: Malware on the victim's device that reads SMS or email for one-time codes.

### Severity: **Critical**

Phishing is the initial access vector for 36% of breaches (Verizon 2024 DBIR). A well-crafted AiTM phishing page can capture both password and session token, rendering even MFA-protected accounts vulnerable. The 2022 Uber breach, 2022 Twilio breach, and 2022-2023 Okta campaign all used AiTM phishing.

### Mitigations (ranked by effectiveness)

1. **Phishing-resistant MFA**: FIDO2/WebAuthn (passkeys, hardware security keys). These are origin-bound — the browser enforces that the credential only works on the legitimate domain. An AiTM proxy at `evil.com` cannot complete WebAuthn authentication for `google.com`. This is the gold standard.
2. **Number matching / QR-code MFA** — replaces push notification approval with explicit challenge-response that ties the authentication to the specific session
3. **DMARC, SPF, DKIM enforcement** — email authentication reducing spoofed sender addresses
4. **Advanced email filtering** — AI/ML-based detection, link rewriting, attachment sandboxing
5. **Security awareness training with simulated phishing** — measurable reduction in click rates over time
6. **Browser-based phishing detection** — Safe Browsing API, EV certificates (declining relevance), password manager domain verification (password managers won't autofill on lookalike domains)
7. **Hardware security key requirement for privileged accounts** — YubiKey/Titan for admin, finance, executive accounts

### Statistics

- Verizon DBIR 2024: phishing as initial access vector in 36% of breaches (including pretexting via email)
- Proofpoint 2024 State of the Phish: 71% of organizations experienced at least one successful phishing attack
- Google Security Blog: Security keys eliminated successful phishing against 85,000+ employees
- CISA: Use of AiTM phishing toolkits grew 1,400% from 2021 to 2023

---

## 5. Password Reuse

### Attack Mechanism

Users reuse passwords because managing unique strong passwords for dozens or hundreds of services is cognitively impossible without tooling. When Service A is breached, attackers test the same email/password combination on Service B, C, and D (credential stuffing, see Section 2). The impact is magnified by:

- **Breach aggregation**: Services like Have I Been Pwned (HIBP) and DeHashed aggregate billions of exposed credentials from thousands of breaches, making them one-click accessible.
- **Password variants**: Users often "vary" passwords (e.g. `Spring2022!` → `Summer2022!` → `Autumn2022!`), which is trivially defeated by rule-based cracking (hashcat rules like `best64.rule`).
- **Email as universal identifier**: Most services use email as the username, making cross-service correlation trivial.

### Severity: **Critical**

Password reuse is the root cause of credential stuffing viability, which accounts for the majority of automated login attacks. A Google/Harris Poll study found 52% of users reuse the same password across multiple accounts, and 13% reuse the same password for ALL accounts.

### Mitigations (ranked by effectiveness)

1. **Breached password detection** on registration and password change (check against HIBP's k-anonymity API or a local bloom filter of known compromised passwords)
2. **Educate and facilitate password manager adoption** — corporate-managed password managers (1Password, Bitwarden) as standard-issue tooling
3. **Passwordless / passkey migration** — eliminates passwords entirely, making reuse impossible
4. **MFA enforcement** — contains the blast radius when reuse does occur
5. **Login anomaly detection** — flag logins from improbable geolocations, new devices, or unusual times

### Statistics

- Google/Harris Poll 2019: 52% reuse passwords across accounts; 13% use the same password for everything
- LastPass Psychology of Passwords 2023: 62% of users reuse passwords despite knowing it's risky
- NIST SP 800-63B: explicitly recommends checking passwords against known compromised password lists
- Collection #1 (2019): 773 million unique email/password pairs in a single breach compilation

---

## 6. Database Breaches

### Attack Mechanism

#### 6a. SQL Injection (SQLi)
Malicious SQL statements injected into application input fields. Classic example: `' OR 1=1 --` in a login form. Despite being a well-understood vulnerability for 20+ years, SQLi remains in the OWASP Top 10 (ranked #3 in 2021). Impact: complete table dump of the users database, including password hashes, emails, PII, and session tokens.

#### 6b. Insider Threats
Legitimate database access abused for credential harvesting. Database administrators, developers with prod access, or compromised employee accounts with read access to credential stores. Difficult to detect because the access appears legitimate.

#### 6c. Exposed Backups
Database dumps left in publicly accessible S3 buckets, unsecured rsync endpoints, exposed `.git` directories, misconfigured MongoDB/Elasticsearch instances with no authentication. Shodan and GreyNoise make discovery trivial.

#### 6d. Logging Credentials
Passwords, tokens, or API keys accidentally logged to application logs, APM tools (Datadog, New Relic), or error tracking services (Sentry). Logs are often less protected than the database itself.

### Severity: **Critical**

A database breach containing password hashes enables offline cracking against all users simultaneously. If hashing is weak and many users have non-random passwords, a high percentage will be cracked. The 2012 LinkedIn breach (6.5M unsalted SHA1 hashes) and the 2013 Adobe breach (153M encrypted/weakly hashed passwords with password hints) are canonical examples of catastrophic hashing failures.

### Mitigations (ranked by effectiveness)

1. **Parameterized queries / prepared statements for ALL database access** — eliminates SQL injection at the root. ORMs provide this by default but hand-written SQL is a risk
2. **Database encryption at rest** (TDE, LUKS, AWS RDS encryption) and **application-level field encryption** for PII columns
3. **Least privilege database access** — application accounts should only have SELECT/INSERT/UPDATE on necessary tables, never DROP/ALTER/GRANT
4. **Audit logging and anomaly detection** — monitor for unusual query patterns, large result sets, off-hours access
5. **Secure backup pipelines** — encrypted backups, access-controlled storage, regular backup deletion testing
6. **Log scrubbing / redaction** — strip or hash sensitive fields before they hit log aggregation; scan existing logs for secrets
7. **Background check and access review for privileged users** — periodic review of who has production database access
8. **Web Application Firewall (WAF)** with SQLi rules — defense-in-depth, not a primary mitigation

### Statistics

- OWASP Top 10 2021: SQL injection ranked #3
- IBM Cost of a Data Breach 2024: average cost of a breach $4.88 million, credential-related breaches highest per-record cost
- Snyk 2023: 53% of organizations discovered secrets in logs
- 2021 S3 bucket exposures: over 2,000 publicly accessible buckets containing PII according to various security researchers

---

## 7. Weak Hashing Algorithms

### Attack Mechanism

The password hashing algorithm determines how computationally expensive it is to crack hashes offline. Weaker algorithms offer minimal protection:

| Algorithm | Hashes/sec (RTX 4090) | 8-char random password (95 chars) crack time |
|---|---|---|
| NTLM | ~313 GH/s | ~6 seconds |
| MD5 | ~164 GH/s | ~11 hours |
| SHA1 | ~53 GH/s | ~34 hours |
| SHA256 (unsalted, single round) | ~23 GH/s | ~3 days |
| PBKDF2-SHA256 (100k iter) | ~1,400 H/s | ~146 million years |
| bcrypt (cost 10) | ~1,000 H/s | ~200 million years |
| bcrypt (cost 12) | ~250 H/s | ~800 million years |
| Argon2id (t=3, m=64MB, p=4) | ~30 H/s | ~6.9 billion years |

*Note: These are for truly random passwords. Most human-chosen 8-char passwords fall to dictionary + rule attacks in minutes regardless of algorithm.*

NTLM and MD5 are effectively "instant" for human-chosen passwords against dictionary attacks. Even SHA256 without iterations and salt is dangerously fast.

### Severity: **Critical** (MD5/SHA1/NTLM used as password storage), **High** (unsalted SHA256), **Low** (bcrypt cost 12+ / Argon2id)

Any system storing passwords with MD5, SHA1, or single-round SHA256 should be treated as storing plaintext for threat modeling purposes.

### Mitigations (ranked by effectiveness)

1. **Use Argon2id** (winner of the Password Hashing Competition, 2015) with tuned parameters: minimum 64MB memory, 3+ iterations, 4+ parallelism. Argon2id resists GPU, ASIC, and side-channel attacks.
2. **bcrypt with cost factor 12+** as fallback if Argon2id library unavailable. bcrypt has been battle-tested for 25 years but lacks memory-hardness.
3. **PBKDF2-SHA256 with 600,000+ iterations** (OWASP 2024 recommendation). Weaker than Argon2id because it's not memory-hard, but widely available in FIPS environments.
4. **scrypt with N=2^17, r=8, p=1** (memory-hard like Argon2id) if available.
5. **Pepper** — application-layer secret (HSM, KMS) combined with salt, so database-only breaches can't crack hashes at all
6. **Hash upgrade path** — on user login, re-hash password with stronger algorithm and update stored hash; transparent to user
7. **Comprehensive migration from MD5/SHA1** — flag old-hash accounts, force password reset on next login

### Statistics

- Hashcat benchmark data (RTX 4090, September 2024): benchmarks listed above
- 2012 LinkedIn breach: 6.5M unsalted SHA1 hashes, >90% cracked within days
- 2013 Adobe breach: 153M encrypted (not hashed) passwords — the encryption key was found in the breach, effectively plaintext
- 2009 RockYou breach: 32M plaintext passwords stored — no hashing at all

---

## 8. Missing Salting

### Attack Mechanism

Without a salt, every instance of the same password produces the identical hash. This enables three attacks:

1. **Rainbow table attack** (see Section 3): A single precomputed table cracks all users' identical hashes instantly.

2. **Password frequency analysis**: The attacker can immediately see which passwords are most common by hash frequency. In a database of 1M users, if hash `H` appears 50,000 times, the attacker can deduce those 50,000 users share a common (likely weak) password. Crack it once, own 50,000 accounts.

3. **Simultaneous attack on all users**: Without salts, an attacker cracking hash `H` cracks the password for ALL users with that hash. With unique salts, the attacker must crack each hash independently — an N-fold increase in work. A database of 1M users with unique salts requires 1M independent cracking operations; without salts, a single operation reveals all users with that password.

### Amplification Example

Consider a breach of 10 million users with `password123` stored as MD5. Without salting: all 10M entries produce the same MD5 hash `482c811da5d5b4bc6d497ffa98491e38`. An attacker runs it through a rainbow table or dictionary and instantly owns every account using that password. With unique salts: the same 10M entries produce 10M different hashes. The attacker must crack each independently. At 164 GH/s, cracking "password123" per hash is ~1 microsecond, so salted vs unsalted matters less for truly trivial passwords. But for passwords like `Tr0ub4dor&3`, where dictionary rules take ~1 second per crack, the difference is ~10 million seconds (115 days) with salts vs 1 second without.

### Severity: **Critical**

Unsalting is a multiplicative vulnerability: it amplifies weak hashing, enables rainbow tables, and reveals password reuse patterns. It's the single most basic and unforgivable authentication storage failure.

### Mitigations (ranked by effectiveness)

1. **Always salt with CSPRNG** — at least 128 bits (16 bytes) of random data, unique per user, using a cryptographically secure random number generator (`/dev/urandom`, `secrets.token_bytes()`, `SecureRandom`)
2. **Use standard library functions** that salt by default: `bcrypt.hashpw()`, `argon2.PasswordHasher().hash()`, `Django.contrib.auth.hashers.make_password()`
3. **Re-salt on password change** — generate a new salt every time a password is set or changed
4. **Pepper (application-level secret)** — adds an additional value known only to the application (not stored in the database), providing defense-in-depth. Store in HSM, KMS, or secure environment variable.
5. **Do not use short or deterministic salts** — no usernames, email addresses, timestamps, or sequential IDs as salts. These make salts guessable and enable precomputation attacks per-username.

### Statistics

- LinkedIn 2012: 6.5M unsalted SHA1 hashes, >90% cracked in days
- Adobe 2013: 153M unsalted (encrypted, with key in the breach) — effectively plaintext
- RockYou 2009: 32M passwords stored in plaintext (no hashing, no salting)
- Ashley Madison 2015: bcrypt with cost 12 (proper salting) — only ~11 million of 36 million passwords cracked despite massive GPU cluster effort

---

## 9. Lack of Multi-Factor Authentication (MFA)

### Attack Mechanism

Single-factor authentication (password only) relies entirely on one secret that can be stolen, guessed, cracked, phished, or intercepted. MFA adds an independent authentication factor from a different category:

- **Knowledge** (password, PIN, security question) — "something you know"
- **Possession** (hardware key, TOTP app, SMS code, push notification) — "something you have"
- **Inherence** (fingerprint, face, iris, voice, behavioral biometrics) — "something you are"

When MFA is absent, any compromise of the password results in full account takeover.

### Account Takeover Rates: With vs Without MFA

| Study | Without MFA | With MFA | Reduction |
|---|---|---|---|
| Microsoft (2023) | 99.9% of compromised accounts had no MFA | <0.1% of compromised accounts had MFA | ~99.9% |
| Google (2019, NYU/UC San Diego) | 100% of automated bot attacks successful | 100% blocked by on-device prompt MFA | 100% |
| Google (2019, same study) | 96% of bulk phishing attacks successful | 99% blocked by on-device prompt MFA | 99% |
| Google (2019, same study) | 76% of targeted attacks successful | 90% blocked by on-device prompt MFA | 90% |

**Not all MFA is equal.** SMS-based MFA is vulnerable to SIM swapping (80% reduction in ATO vs single-factor per NIST estimates). Push notification MFA is vulnerable to MFA fatigue attacks (~90-95% effective). FIDO2/WebAuthn hardware keys are phishing-resistant and effectively prevent 100% of remote phishing/credential stuffing attacks based on real-world data.

### Severity: **Critical** (for sensitive accounts), **High** (for all accounts)

Given that 99.9% of compromised Microsoft accounts lacked MFA, the absence of MFA is the single strongest predictor of account takeover.

### Mitigations (ranked by effectiveness)

1. **FIDO2/WebAuthn (passkeys, security keys)** — phishing-resistant, origin-bound, no shared secret. Highest assurance level (AAL3 per NIST SP 800-63).
2. **Time-based One-Time Password (TOTP)** via authenticator app — no cellular dependency, reasonable user experience. AAL2.
3. **Push notification with number matching** — better than simple approve/deny. Requires user to enter a number displayed on the login screen into the app.
4. **Hardware TOTP tokens** (RSA SecurID, YubiKey OATH) — physical device, AAL2.
5. **SMS / voice call OTP** — last resort. Vulnerable to SIM swap, SS7 interception, and malware. Limit to low-risk scenarios. NIST SP 800-63B deprecates SMS as a restricted authenticator.
6. **Step-up authentication** — require MFA for sensitive operations (password change, email change, wire transfer) even if login didn't require it

### Statistics

- Microsoft: 99.9% of compromised accounts lacked MFA (2023)
- Google/NYU/UC San Diego 2019 study on-device prompt MFA effectiveness:
  - 100% of automated bots blocked
  - 99% of bulk phishing blocked
  - 90% of targeted attacks blocked
- CISA: organizations with MFA deployed experience 80-90% fewer successful account takeovers
- Twitter 2020 breach: attackers used phone spear-phishing to compromise employee credentials; accounts without MFA were the first compromised

---

## 10. Insecure Password Reset Flows

### Attack Mechanism

Password reset is often the weakest link in authentication security because it bypasses the password entirely. Attack vectors include:

#### 10a. Token Predictability
Reset tokens generated using predictable sources: `md5(username + timestamp)`, sequential numbers, or weak PRNGs (e.g. `rand()` in PHP). Attackers can predict valid tokens without receiving the email.

#### 10b. Email Interception
Reset tokens sent over unencrypted email (no TLS). Email accounts themselves often lack MFA, so compromising the email account grants access to password resets for all linked services — a single point of failure.

#### 10c. Missing Rate Limits
No limit on reset attempts per email or per IP. Attackers can enumerate valid accounts (username oracle) by observing response differences between valid and invalid emails. Attackers can also brute-force 6-digit numeric tokens (1M combinations) in minutes if rate limits are absent.

#### 10d. Lack of Token Expiry
Reset tokens that never expire (or have multi-day validity). A token sent 6 months ago could still be valid. If it was logged, stored in browser history, or exposed in any other way, the account is compromised.

#### 10e. Knowledge-Based Authentication (KBA)
"Security questions" (mother's maiden name, pet's name, first school) are trivially defeated:
- Answers are often publicly available (Facebook, genealogy sites)
- Answers to common questions have low entropy (e.g. 20 common "first car" models)
- Same questions across many sites = one breach reveals answers for all services
- Google study: 40% of users can't remember their own security question answers

### Severity: **High** (reset flow is the #1 account takeover path when well-designed login security is bypassed)

A poorly implemented reset flow can render even strong passwords, MFA, and hashing irrelevant. This is an exceptionally common vulnerability in real-world applications.

### Mitigations (ranked by effectiveness)

1. **CSPRNG-generated tokens** — minimum 128 bits of entropy, generated via cryptographically secure random number generator. At least 20 hex characters (80 bits) minimum, 32 recommended.
2. **Short expiry** — tokens should expire in 15-60 minutes maximum. Not 24 hours, not "never."
3. **Single-use tokens** — invalidated immediately on use. No replay attacks.
4. **Rate limiting** — per-email AND per-IP rate limits on token generation AND token submission attempts. Prevent enumeration and brute-force.
5. **Constant-time comparison** — token validation must use timing-safe comparison (`hash_equals()` in PHP, `secrets.compare_digest()` in Python) to prevent timing side-channel attacks on token matching.
6. **Generic error messages** — "If an account with that email exists, a reset link has been sent." No differentiation between valid and invalid email addresses.
7. **No knowledge-based questions** — NIST SP 800-63B explicitly prohibits KBA as an authenticator. Do not use.
8. **Notify on reset** — email the user when a reset is requested and when a password is successfully changed. "If this wasn't you, contact support immediately."
9. **Require existing session or second factor** — for already-logged-in users changing their password, require the current password or MFA. For logged-out reset, require access to the email account (which should itself have MFA).
10. **Do not expose tokens in URL after redirect** — many web servers, proxies, and analytics tools log request URLs including query parameters. Use POST with form body for token submission.

### Statistics

- OWASP Forgot Password Cheat Sheet: token predictability and enumeration are among most common vulnerabilities
- Google 2015: 40% of users couldn't answer their own security questions accurately
- Microsoft Research 2015: 40% success rate for acquaintances guessing security question answers for each other
- HackerOne reports: password reset token issues consistently rank in top 10 vulnerability types by bounty payout

---

## 11. Session Hijacking

### Attack Mechanism

After successful authentication, the session is the user's identity until logout or expiration. Session hijacking steals that identity:

#### 11a. Session Fixation
Attacker obtains a valid session ID (e.g. by visiting the login page), then tricks the victim into authenticating using that same session ID (via a link, XSS, or cookie injection). After victim logs in, the attacker uses the same session ID to access the authenticated session. The root cause: the application does not regenerate the session ID after privilege change (login, role elevation).

#### 11b. XSS Cookie Theft
Cross-Site Scripting (XSS) enables `document.cookie` access in JavaScript. If session cookies lack the `HttpOnly` flag, injected scripts can exfiltrate them to attacker-controlled servers.

#### 11c. Missing Cookie Security Flags
- **Missing `HttpOnly`**: Cookie accessible via JavaScript (`document.cookie`). Any XSS vulnerability becomes session hijacking.
- **Missing `Secure`**: Cookie transmitted over unencrypted HTTP. Man-in-the-middle (MITM) on public Wi-Fi, rogue access points, or ARP spoofing can capture the cookie.
- **Missing `SameSite`**: Cookie sent with cross-site requests. CSRF attacks can include the session cookie in forged requests. `SameSite=Lax` is the modern minimum; `SameSite=Strict` for high-security applications.

#### 11d. Session Token in URL
Session IDs in query parameters (`?sessionid=abc123` or `?jsessionid=abc123`) are logged by:
- Web server access logs
- Proxy/cache servers
- Referer headers sent to third-party analytics, CDNs, or embedded resources
- Browser history
- Copy-pasted/shared URLs

This is sometimes called "session riding" and was common in Java Servlet applications (jsessionid URL rewriting).

### Severity: **High**

Session hijacking is a high-severity attack because it bypasses all authentication controls — the attacker doesn't need the password, MFA, or any credential. With a valid session, they are the user.

### Mitigations (ranked by effectiveness)

1. **Regenerate session ID on authentication** — every login, logout, and privilege change (user → admin) must generate a new, cryptographically random session ID. This defeats session fixation.
2. **Set `HttpOnly` flag on session cookies** — prevents JavaScript access. Defense-in-depth against XSS.
3. **Set `Secure` flag on session cookies** — prevents transmission over unencrypted HTTP. Requires full HTTPS deployment.
4. **Set `SameSite=Lax`** (default modern browsers) or `SameSite=Strict` — prevents cross-site request forgery and cross-site cookie access.
5. **Set `__Host-` cookie prefix** — enforces both `Secure` and `Path=/` attributes via browser enforcement. `Set-Cookie: __Host-sessionid=...; Secure; Path=/; SameSite=Lax; HttpOnly`
6. **Naver include session tokens in URLs** — cookies only. No URL rewriting.
7. **Content Security Policy (CSP)** — limits JavaScript execution sources, mitigating XSS-based cookie theft even if `HttpOnly` is somehow bypassed
8. **Session timeout** — absolute timeout (e.g. 12 hours) and idle timeout (e.g. 30 minutes) so stolen sessions are time-limited
9. **Server-side session invalidation** — "logout everywhere" functionality, session revocation on password change
10. **TLS 1.3 deployment** — modern TLS with perfect forward secrecy

### Statistics

- OWASP Top 10 (2021): A07:2021-Identification and Authentication Failures includes session management
- HackerOne 2023: Session management vulnerabilities account for approximately 7% of all reported web vulnerabilities
- XSS remains in OWASP Top 10 2021 (A03:2021-Injection), enabling cookie theft when HttpOnly is absent
- Sessions in URLs (CWE-598) formally deprecated by OWASP and all major frameworks since ~2010, yet still found in legacy applications

---

## 12. Password Policy Effectiveness

### Attack Mechanism

Poor password policies create a false sense of security while frustrating users into workarounds (Post-it notes, password reuse, predictable patterns like `CompanyName2024!`).

#### NIST SP 800-63B Modern Guidance (2024)

NIST's Digital Identity Guidelines fundamentally changed password policy philosophy:

| Policy Element | Old Practice (2003-2017) | NIST SP 800-63B (2017-2024) |
|---|---|---|
| Minimum length | 8 characters | 8 characters minimum for user-generated; 6 for randomly generated |
| Maximum length | Often 16-20 characters | 64 characters minimum (128 recommended) |
| Complexity rules | Must include uppercase, lowercase, digit, special | No composition rules |
| Password hints | Allowed | Prohibited |
| Knowledge-based auth (KBA) | Security questions | Prohibited |
| Mandatory rotation | Every 30/60/90 days | Prohibited unless evidence of compromise |
| Breached password check | Not mentioned | REQUIRED at establishment and change |
| Copy/paste in password fields | Often disabled | Allowed (facilitates password manager use) |
| Show password while typing | Often disabled | Allowed (reduces typos, encourages longer passwords) |
| Password strength meters | Not mentioned | Recommended for user guidance |

**Rationale for the changes:**

- **Composition rules backfire**: Users respond to `Must include Uppercase, Digit, Special` by making minimal, predictable transformations: `password` → `Password1!`. This satisfies the rule but provides negligible security gain while frustrating users who want to use passphrases.
- **Mandatory rotation reduces security**: When forced to change passwords frequently, users choose weaker passwords, use predictable patterns (`Spring2024!` → `Summer2024!` → `Autumn2024!`), or write passwords down. NIST, Microsoft, NCSC (UK), ASD (Australia), and BSI (Germany) all recommend against mandatory rotation without evidence of compromise.
- **Breached password check is the highest-impact policy**: Checking passwords against known breach corpuses eliminates the most commonly cracked passwords. This single check prevents dictionary, credential stuffing, and rainbow table attacks against the weakest passwords.

### Severity: **Medium** (policy failure doesn't directly attack but creates systemic vulnerability)

Poor password policies don't directly exploit accounts but increase the entire user base's vulnerability to all other attack vectors. The severity depends on the specific failure.

### Mitigations (ranked by effectiveness)

1. **Implement breached password detection** — use k-anonymity model (HIBP API) to check passwords at creation and change without revealing the full password to any third party
2. **Remove composition rules** — enforce only minimum length (12+ for user-generated passwords is a strong recommendation beyond NIST's 8-char minimum)
3. **Allow all character types** — Unicode, spaces, emoji. A passphrase with spaces (`correct horse battery staple`) is far stronger and more usable than `Tr0ub4dor&3`
4. **Remove mandatory rotation policy** — replace with event-driven changes: evidence of compromise, high-risk activity, user request
5. **Allow password managers** — permit paste, remove max-length limits below 128, don't use JavaScript to block autofill
6. **Provide a password strength meter** — zxcvbn (Dropbox), Kaspersky, or NIST entropy estimator, calibrated against real-world cracking techniques
7. **Set maximum length to 128+ characters** — accommodate passphrases and password manager-generated credentials
8. **Remove password hints and KBA** — if an attacker can research the answer or guess it with 10 attempts, it's not an authenticator

### Statistics

- Microsoft 2019 study: Removing mandatory password rotation saved $7M+ per year in help desk costs, and account compromise rates did NOT increase
- NIST SP 800-63B (2017): "Verifiers SHOULD NOT require memorized secrets to be changed arbitrarily (e.g., periodically)"
- NCSC (UK, 2016): "Regular password changing harms rather than improves security"
- Carnegie Mellon 2010 study: Users forced to change passwords every 90 days chose passwords 46% weaker than users not forced to rotate
- HIBP Pwned Passwords: Over 850 million unique passwords in the breached password corpus as of 2024

---

## Policy Dimension Assessments

---

### A. Password Length vs Complexity Rules Effectiveness

**Length is overwhelmingly more important than complexity.**

The math is dispositive:

- 6-character complex password (uppercase + lowercase + digit + special = 95^6): ~7.4 x 10^11 combinations
- 12-character lowercase-only password (26^12): ~9.5 x 10^16 combinations
- The 12-character lowercase-only password has **~130,000x more combinations** than the 6-character "complex" password

Human factors reinforce this:
- `Tr0ub4dor&3` (11 chars, "complex"): hashcat cracks this with dictionary+rule attack in seconds
- `correct horse battery staple` (28 chars, all lowercase with spaces): effectively uncrackable via brute-force, yet far easier to remember and type

**NIST conclusion (SP 800-63B):** "Composition rules provide less benefit than previously thought and are a significant cause of user frustration. Length shall be the primary memorized secret characteristic." Abandon complexity rules. Require 8 characters minimum; strongly recommend 12+.

**Industry data:**
- Dropbox zxcvbn research: Composition requirements increase password strength by ~1 bit (2x harder to crack). Increasing minimum length by 2 characters increases strength by ~12 bits (4,096x harder).
- Microsoft Research: The most common transformation pattern converting dictionary words to "complex" passwords (e.g., `password` → `P@ssw0rd`) is well-known to hashcat and provides no meaningful security.

---

### B. Mandatory Password Rotation

**Pro-rotation arguments (outdated):**
- Limits the window of exposure for an undetected compromised password
- Ensures former employees can't access accounts (though this should be handled by deprovisioning)
- Was a compliance requirement for many frameworks (PCI DSS pre-4.0)

**Cons (supported by current evidence):**
- Users select weaker passwords when forced to change frequently (Carnegie Mellon: 46% weaker)
- Predictable transformation patterns: incrementing numbers (`Password1` → `Password2`), seasonal patterns (`Winter2024!` → `Spring2024!`)
- Password reuse across accounts INCREASES because users can't remember dozens of frequently-changing passwords
- High help desk costs: 20-50% of IT support tickets are password resets (Forrester/Gartner estimates)
- Writing passwords down (Post-it notes, digital notes) increases

**Modern consensus:**
- NIST SP 800-63B: "Verifiers SHOULD NOT require memorized secrets to be changed arbitrarily (e.g., periodically). However, verifiers SHALL force a change if there is evidence of compromise of the authenticator."
- NCSC (UK): Recommends against regular password expiry
- PCI DSS 4.0 (March 2022): Removed the 90-day mandatory password change requirement IF other controls are in place (MFA, breached password detection, monitoring)

**Recommendation:** Replace mandatory rotation with: breached password detection, MFA enforcement, anomaly-based forced resets (impossible travel, credential stuffing indicators, dark web monitoring), and event-driven rotations (compromise evidence, user request, role change).

---

### C. Breached Password Detection

This is the single highest-impact change recommended by NIST SP 800-63B.

**Mechanism:**
1. User enters a new password (at registration or password change)
2. The password is hashed (typically SHA1 for HIBP compatibility) client-side or server-side
3. Only the first 5 characters of the hex-encoded hash are sent to the HIBP k-anonymity API
4. The API returns all hash suffixes (remaining 35 hex characters) for hashes starting with that 5-char prefix
5. The server checks if the full hash is in the returned list
6. If found, the password is rejected as known-compromised

This preserves privacy: the full hash never leaves the application, HIBP never learns who is checking what, and k-anonymity ensures the query prefix maps to hundreds of hashes.

**Why it's effective:**
- Eliminates the 100,000-1,000,000 most commonly breached passwords that would appear in any credential stuffing list
- Prevents users from using passwords exposed in previous breaches
- Combined with MFA, eliminates the credential stuffing threat vector
- Near-zero user friction beyond "that password has been compromised, choose another"

**Industry adoption:**
- NIST SP 800-63B: REQUIRED (SHALL check against known compromised values)
- NCSC (UK): recommends checking against compromised lists
- Microsoft: Azure AD Password Protection bans over 1,000 globally banned passwords plus organization-specific custom lists
- 1Password/Bitwarden/Dashlane: integrated Watchtower/HIBP checking by default

---

### D. Password Strength Meters

**Most meters are misleading and counterproductive.**

Common problems with basic meters (regex rules-based):
- `Password1!` scores "Strong" on many meters because it has uppercase, lowercase, digit, and special character
- `correcthorsebatterystaple` scores "Weak" because it lacks digits/specials despite having ~118 bits of entropy (uncrackable)
- No awareness of dictionary attacks, keyboard walks (`qwerty123`), or common substitutions (`@` for `a`, `3` for `e`)

**Effective meters (e.g. zxcvbn by Dropbox):**
- Uses actual password lists, common names, English words, keyboard patterns, dates, and sequences
- Estimates crack time using composition-aware entropy estimation plus known attack patterns
- Calibrated against real hashcat cracking speeds with standard rulesets
- Provides actionable feedback: "Add another word or two. Uncommon words are better." rather than "Must include at least one digit."

**Metrics:**
- zxcvbn has been adopted by Dropbox, GitHub, and numerous Fortune 500 login forms
- Studies show zxcvbn-based feedback increases average password entropy by 10-15 bits
- Carnegie Mellon 2012: Meters that provided detailed, specific feedback (rather than red/yellow/green indicators) produced 42% stronger passwords
- Meters that displayed crack time estimates (seconds, hours, years) were more motivating than meters that displayed abstract "strength" categories

**Recommendation:** Deploy a modern, attack-aware password strength estimator (zxcvbn or equivalent), provide specific guidance rather than rejection rules, and integrate with breached password detection. The meter should guide, not enforce.

---

## Summary Risk Matrix

| Threat Vector | Severity | Mitigation Priority | Prevalence |
|---|---|---|---|
| Brute-Force (offline) | Critical | 1 — Argon2id/bcrypt + length min | Universal |
| Credential Stuffing | Critical | 1 — MFA + breached pwd check | Very High (193B attempts/yr) |
| Rainbow Tables | Medium (modern), Critical (legacy) | 1 — Salting (mandatory) | Low (modern), High (legacy) |
| Phishing | Critical | 1 — FIDO2/WebAuthn, training | Very High (36% of breaches) |
| Password Reuse | Critical | 1 — Breached pwd detection, MFA | Very High (52%+ of users) |
| Database Breaches | Critical | 1 — Parameterized queries, least privilege | High |
| Weak Hashing (MD5/SHA1/SHA256) | Critical | 1 — Argon2id migration | Moderate (declining) |
| Missing Salting | Critical | 1 — Always salt, always | Low (modern) |
| Lack of MFA | Critical | 1 — Universal MFA deployment | High (varies by sector) |
| Insecure Reset Flows | High | 1 — Cryptographically random tokens, short expiry | Moderate |
| Session Hijacking | High | 1 — HttpOnly/Secure/SameSite, session rotation | Moderate |
| Password Policy Failures | Medium | 2 — NIST 800-63B alignment | Very High (legacy policies prevalent) |

---

## References

- NIST SP 800-63B — Digital Identity Guidelines: Authentication and Lifecycle Management (2024 update)
- OWASP Authentication Cheat Sheet, Password Storage Cheat Sheet, Forgot Password Cheat Sheet
- OWASP Top 10 (2021)
- Verizon Data Breach Investigations Report (DBIR) 2024
- Microsoft Digital Defense Report 2023
- Google/NYU/UC San Diego — "Protecting Accounts from Credential Stuffing with Password Breach Alerting" (USENIX 2019)
- Hashcat benchmark data (RTX 4090, September 2024)
- Dropbox zxcvbn: Low-Budget Password Strength Estimation (USENIX 2016)
- Troy Hunt / Have I Been Pwned — Pwned Passwords (k-anonymity model documentation)
- NCSC (UK) — Password Policy Guidance (2016, updated 2023)
- PCI DSS 4.0 (March 2022)
- Carnegie Mellon University — "The Security of Modern Password Expiration" (2010)
- FIDO Alliance — WebAuthn Specification and Security Analysis
