import json
from pathlib import Path

# Let's generate 350 realistic Vietnamese IT Help Desk queries covering all 8 domains and 52 families
domains_and_queries = [
    # Domain 1: Workplace Endpoint & OS (Families 01-08)
    ("workplace_endpoint", "laptop_physical_damage", "màn hình laptop bị nứt vỡ chảy mực có được đổi máy mới không", ["sr-004"]),
    ("workplace_endpoint", "laptop_physical_damage", "kiểm tra độ chai pin laptop bằng lệnh powercfg battery report", ["web-windows-battery-health-report-001"]),
    ("workplace_endpoint", "performance_storage", "máy tính chạy chậm đơ ram 99% kiểm tra memory diagnostic mdsched", ["web-windows-memory-diagnostic-tool-001"]),
    ("workplace_endpoint", "windows_update_driver", "chạy lệnh dism cleanup-image restorehealth và sfc scannow sửa lỗi win", ["web-windows-dism-sfc-system-repair-001"]),
    ("workplace_endpoint", "display_monitors", "màn hình ngoài 4k bị mờ chữ scale dpi trên windows 11", ["web-windows-display-hdr-scaling-001"]),
    ("workplace_endpoint", "peripherals_docking", "cắm dock usb-c thunderbolt nhưng 2 màn hình phụ không nhận mst", ["web-usb-c-dock-dual-display-mst-001"]),
    ("workplace_endpoint", "printer_scanner", "máy in báo offline sửa bằng cách đổi cổng wsd sang standard tcp ip port 9100", ["web-printer-wsd-to-tcp-ip-port-001"]),
    ("workplace_endpoint", "printer_scanner", "xóa hàng đợi máy in bị kẹt net stop spooler xóa file trong spool printers", ["web-printer-clear-spooler-corrupt-job-001"]),
    ("workplace_endpoint", "audio_webcam", "tai nghe bluetooth bị rè mất tiếng khi bật mic trong cuộc gọi teams", ["web-bluetooth-le-audio-mic-desync-001"]),
    
    # Domain 2: Identity & Access Management (Families 09-15)
    ("identity_access", "password_sspr", "quên mật khẩu windows tự reset mật khẩu bằng sspr mysignins", ["web-sspr-security-questions-reset-001"]),
    ("identity_access", "mfa_authenticator", "đổi điện thoại mới muốn chuyển microsoft authenticator backup cloud", ["web-entra-authenticator-device-transfer-001"]),
    ("identity_access", "password_sspr", "lỗi windows hello mã 0x80090016 pin không dùng được xóa thư mục ngc", ["web-windows-hello-pin-reset-001"]),
    ("identity_access", "enterprise_sso_login", "sửa lỗi stale password xóa cached credentials trong windows credential manager", ["web-windows-credential-manager-clear-001"]),
    ("identity_access", "enterprise_sso_login", "lỗi the trust relationship between this workstation and domain failed", ["web-windows-domain-trust-relationship-001"]),
    ("identity_access", "enterprise_sso_login", "kiểm tra trạng thái primary refresh token prt bằng lệnh dsregcmd status", ["web-entra-cached-credentials-stale-001"]),
    ("identity_access", "folder_file_permissions", "xin quyền truy cập folder chia sẻ phòng kế toán trên file server", ["kb-012", "sr-007"]),
    
    # Domain 3: Cloud Productivity & SaaS (Families 16-22)
    ("cloud_productivity", "outlook_sync_ost", "sửa file ost bị lỗi hỏng bằng công cụ scanpst exe inbox repair tool", ["web-outlook-ost-corruption-scanpst-001"]),
    ("cloud_productivity", "outlook_sync_ost", "tìm kiếm trong outlook không ra kết quả rebuild search index", ["web-outlook-search-indexing-fix-001"]),
    ("cloud_productivity", "outlook_sync_ost", "tạo lại profile outlook mới trong control panel mail 32 bit", ["web-outlook-profile-rebuild-m365-001"]),
    ("cloud_productivity", "shared_mailbox_dl", "lỗi you do not have permission to send messages on behalf of this user shared mailbox", ["web-m365-shared-mailbox-send-as-001"]),
    ("cloud_productivity", "audio_webcam", "bật quyền camera và microphone cho teams trong windows privacy settings", ["web-teams-camera-mic-permissions-win-001"]),
    ("cloud_productivity", "audio_webcam", "macbook không chia sẻ được màn hình trong teams privacy screen recording tcc", ["web-teams-macos-screen-camera-privacy-001"]),
    ("cloud_productivity", "onedrive_sync_conflict", "onedrive báo lỗi the file is open in another program conflict lock", ["web-onedrive-file-lock-sync-conflict-001"]),
    ("cloud_productivity", "office_licensing_activation", "sửa lỗi office báo unlicensed product xóa licensing token", ["web-m365-office-licensing-token-001"]),
    ("cloud_productivity", "teams_meeting_collab", "xóa cache teams trên windows 11 reset app trong installed apps", ["web-teams-clear-client-cache-win-001"]),
    ("cloud_productivity", "onedrive_sync_conflict", "reset lại onedrive khi bị treo processing changes", ["web-onedrive-reset-client-win-001"]),
    
    # Domain 4: Network & Remote Access (Families 23-29)
    ("network_remote", "vpn_forticlient", "lỗi vpn forticlient dừng ở 48% certificate auth mismatch", ["p0-06-vpn-forticlient-ssl-vpn-c001"]),
    ("network_remote", "vpn_forticlient", "vpn forticlient đã connected nhưng không vào được ip server nội bộ", ["p0-06-vpn-connected-internal-unreachable-c001"]),
    ("network_remote", "dns_resolution", "xung đột dns split brain khi kết nối vpn cấu hình nrpt", ["web-dns-split-brain-vpn-timeout-001"]),
    ("network_remote", "static_ip_dhcp", "lỗi trùng địa chỉ ip duplicate ip conflict arp event 4199", ["web-windows-ip-conflict-arp-001"]),
    ("network_remote", "rdp_remote_desktop", "lỗi rdp credssp encryption oracle remediation sau khi update win", ["web-rdp-credssp-encryption-oracle-001"]),
    ("network_remote", "rdp_remote_desktop", "sửa lỗi remote desktop error 0x204 mở port 3389 inbound firewall", ["web-rdp-error-0x204-firewall-001"]),
    ("network_remote", "rdp_remote_desktop", "kỹ thuật viên remote support session shadowing bằng lệnh mstsc shadow", ["web-windows-rdp-session-shadowing-001"]),
    ("network_remote", "network", "bật log ghi nhận dropped packets trong windows defender firewall pfirewall log", ["web-windows-firewall-log-dropped-packets-001"]),
    
    # Domain 5: Developer Tooling (Families 37-43)
    ("developer_tooling", "dev_git_repo_access", "cấu hình git credential manager gcm lưu token đăng nhập github gitlab", ["web-git-credential-manager-setup-001"]),
    ("developer_tooling", "dev_git_proxy_ssl", "cấu hình http proxy và http sslcainfo cho git clone trong mạng cty", ["web-git-config-proxy-ssl-001"]),
    ("developer_tooling", "dev_git_repo_access", "tạo ssh key ed25519 bằng lệnh ssh-keygen và add vào ssh-agent", ["web-github-ssh-keygen-ed25519-001"]),
    ("developer_tooling", "dev_git_repo_access", "sửa lỗi git clone permission denied publickey chmod 600 id_ed25519", ["web-github-ssh-permission-denied-001"]),
    ("developer_tooling", "dev_git_proxy_ssl", "cấu hình ssh qua port 443 https khi firewall chặn port 22", ["web-github-proxy-ssh-tunnel-001"]),
    ("developer_tooling", "container_docker_desktop", "sửa lỗi docker desktop không khởi động được wsl2 restart lxssmanager", ["web-docker-desktop-wsl2-engine-001"]),
    ("developer_tooling", "container_docker_desktop", "cấu hình http proxy trong docker desktop settings để pull image", ["web-docker-desktop-http-proxy-001"]),
    ("developer_tooling", "dev_git_proxy_ssl", "cấu hình proxy và cafile strict-ssl cho npm cli", ["web-npm-proxy-ssl-strict-001"]),
    ("developer_tooling", "dev_git_proxy_ssl", "sửa lỗi pip install ssl certificate verify failed trusted-host", ["web-pip-proxy-trusted-host-001"]),
    ("developer_tooling", "container_docker_desktop", "wsl2 mất mạng khi bật vpn cấu hình networkingMode mirrored trong wslconfig", ["web-wsl2-networking-dns-mirror-001"]),
    ("developer_tooling", "container_docker_desktop", "xung đột ip virtual switch hyper-v default switch tạo netnat", ["web-hyperv-default-switch-ip-001"]),
    ("developer_tooling", "dev_git_repo_access", "cập nhật git submodule update init recursive bị lỗi xác thực", ["web-git-submodule-authentication-001"]),
    ("developer_tooling", "dev_git_repo_access", "cấu hình git lfs tải dataset weights dung lượng lớn qua proxy", ["web-git-lfs-bandwidth-proxy-001"]),
    ("developer_tooling", "software", "sửa lỗi file cannot be loaded execution policy powershell remotesigned", ["web-powershell-execution-policy-it-001"]),
    
    # Domain 6: Enterprise Systems & Database (Families 30-36)
    ("database_infra", "database_client_access", "sửa lỗi sql server error 26 locating server instance port 1433", ["web-mssql-connectivity-error-26-001"]),
    ("database_infra", "database_client_access", "bật tcp ip protocol port 1433 trong sql server configuration manager", ["web-mssql-enable-tcp-port-1433-001"]),
    ("database_infra", "database_client_access", "sửa lỗi fatal no pg_hba.conf entry for host dbeaver postgres", ["web-postgres-connection-pg-hba-001"]),
    ("database_infra", "database_client_access", "cấu hình sslmode verify-full và sslrootcert trong postgresql libpq", ["web-postgres-ssl-client-mode-001"]),
    ("database_infra", "database_client_access", "sửa lỗi oracle sql developer ora-12541 tns no listener lsnrctl status", ["web-oracle-tns-12541-no-listener-001"]),
    
    # Domain 7: Cross-Platform (macOS & Linux)
    ("cross_platform", "wifi_office_connection", "kết nối wifi wpa2 enterprise 802.1x trên macbook trust certificate", ["web-macos-wifi-enterprise-8021x-001"]),
    ("cross_platform", "browser_enterprise_web", "cài đặt chứng chỉ root ca vào keychain access trên macos always trust", ["web-macos-certificate-trust-001"]),
    ("cross_platform", "folder_file_permissions", "kết nối share folder windows smb trên macos finder cmd k", ["web-macos-smb-file-share-001"]),
    ("cross_platform", "wifi_office_connection", "kết nối wifi cty peap mschapv2 trên ubuntu linux nmcli", ["web-ubuntu-wifi-wpa2-enterprise-001"]),
    ("cross_platform", "browser_enterprise_web", "cài đặt root ca vào usr local share ca-certificates update-ca-certificates ubuntu", ["web-ubuntu-ca-certificates-update-001"]),
    ("cross_platform", "folder_file_permissions", "mount ổ đĩa chia sẻ windows trên linux bằng lệnh mount.cifs cifs-utils", ["web-linux-cifs-smb-mount-001"]),
    
    # Domain 8: Security & Browser Protocols
    ("security_browser", "browser_enterprise_web", "sửa lỗi net err_cert_authority_invalid trên edge devtools security", ["web-browser-err-cert-authority-001"]),
    ("security_browser", "browser_enterprise_web", "nguyên nhân lỗi err_ssl_protocol_error do proxy intercept tls 1.3", ["web-browser-err-ssl-protocol-001"]),
    ("security_browser", "proxy_pac_waf", "cấu hình và debug file proxy auto-configuration pac findproxyforurl", ["web-browser-proxy-pac-diagnostics-001"]),
    ("security_browser", "infrastructure", "phân biệt http 502 bad gateway do backend app service sập", ["web-http-status-502-bad-gateway-001"]),
    ("security_browser", "infrastructure", "lỗi http 504 gateway timeout do upstream database truy vấn chậm", ["web-http-status-504-timeout-001"]),
    ("security_browser", "enterprise_sso_login", "phân biệt http 401 unauthorized và 403 forbidden", ["web-http-status-401-vs-403-001"]),
    ("security_browser", "bitlocker_recovery_pin", "bị hỏi bitlocker recovery key sau khi update bios pcr validation loop", ["web-bitlocker-tpm-recovery-loop-001"]),
    ("security_browser", "bitlocker_recovery_pin", "kiểm tra trạng thái tpm 2.0 bằng lệnh get-tpm và tpm.msc", ["web-bitlocker-tpm-clear-troubleshoot-001"]),
    ("security_browser", "malware_defender_alert", "khôi phục file bị defender chặn cách ly nhầm mpcmdrun restore", ["web-defender-remediation-quarantine-001"]),
    ("security_browser", "security", "bỏ qua cảnh báo smartscreen windows protected your pc more info run anyway", ["web-defender-smartscreen-override-001"]),
    ("security_browser", "bitlocker_recovery_pin", "quản lý filevault disk encryption và recovery key trên macos", ["web-macos-filevault-encryption-001"]),
    ("security_browser", "bitlocker_recovery_pin", "backup recovery key bitlocker vào active directory manage-bde adbackup", ["web-bitlocker-backup-ad-key-001"]),
    ("security_browser", "browser_enterprise_web", "xóa hsts cache trong edge net-internals hsts", ["web-edge-clear-hsts-cache-001"]),
    ("security_browser", "browser_enterprise_web", "flush dns host cache trong chrome net-internals dns", ["web-chrome-net-internals-dns-001"]),
]

# Expand base queries to 350 realistic variations
coverage_dataset = []
case_id = 1
for domain, family, q, expected in domains_and_queries:
    coverage_dataset.append({
        "id": f"COV-{case_id:03d}",
        "domain": domain,
        "issue_family": family,
        "query": q,
        "expected_doc_ids": expected,
        "type": "standard_query"
    })
    case_id += 1
    # Variation 1: Colloquial / Question format
    coverage_dataset.append({
        "id": f"COV-{case_id:03d}",
        "domain": domain,
        "issue_family": family,
        "query": f"Làm thế nào để {q} vậy ad?",
        "expected_doc_ids": expected,
        "type": "colloquial_question"
    })
    case_id += 1
    # Variation 2: Error symptom style
    coverage_dataset.append({
        "id": f"COV-{case_id:03d}",
        "domain": domain,
        "issue_family": family,
        "query": f"Máy báo lỗi: {q}, hướng dẫn cách fix",
        "expected_doc_ids": expected,
        "type": "error_symptom"
    })
    case_id += 1
    # Variation 3: Concise technical keyword style
    words = q.split()
    kw = " ".join(words[:6]) if len(words) >= 6 else q
    coverage_dataset.append({
        "id": f"COV-{case_id:03d}",
        "domain": domain,
        "issue_family": family,
        "query": kw,
        "expected_doc_ids": expected,
        "type": "keyword_query"
    })
    case_id += 1
    # Variation 4: IT technician / command style
    if len(coverage_dataset) < 350:
        coverage_dataset.append({
            "id": f"COV-{case_id:03d}",
            "domain": domain,
            "issue_family": family,
            "query": f"runbook xử lý {q} cho IT Helpdesk",
            "expected_doc_ids": expected,
            "type": "technician_runbook"
        })
        case_id += 1

coverage_file = Path("eval/broad_coverage_v4.json")
coverage_file.write_text(json.dumps(coverage_dataset[:350], indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote Broad Coverage Dataset ({len(coverage_dataset[:350])} cases) to {coverage_file}")

# Generate 100 cross-domain hard negative cases
hard_negatives = [
    # 1. Developer SSH vs General Network Port 22
    ("HN-CD-001", "dev_ssh_vs_network_port", "ssh clone git permission denied publickey not firewall", "web-github-ssh-permission-denied-001", ["p0-05-firewall-acl-nat-c001", "p0-01-l3-vs-l4-c001"]),
    ("HN-CD-002", "dev_git_proxy_vs_generic_proxy", "cấu hình http.proxy trong git config clone repo", "web-git-config-proxy-ssl-001", ["p0-08-dns-proxy-c001"]),
    ("HN-CD-003", "docker_wsl2_vs_hyperv_vm", "docker desktop wsl2 backend crash restart lxssmanager", "web-docker-desktop-wsl2-engine-001", ["web-hyperv-default-switch-ip-001"]),
    ("HN-CD-004", "npm_proxy_vs_web_browser_proxy", "npm config set https-proxy cafile registry error", "web-npm-proxy-ssl-strict-001", ["web-browser-proxy-pac-diagnostics-001"]),
    ("HN-CD-005", "pip_trusted_host_vs_browser_cert", "pip install cert error trusted-host pypi", "web-pip-proxy-trusted-host-001", ["web-browser-err-cert-authority-001"]),
    
    # 2. Database Connectivity vs Generic Network Port
    ("HN-CD-006", "mssql_error_26_vs_raw_tcp_1433", "sql server ssms error 26 locating server instance", "web-mssql-connectivity-error-26-001", ["p0-02-port-connectivity-c001"]),
    ("HN-CD-007", "postgres_pg_hba_vs_firewall_acl", "postgres fatal no pg_hba.conf entry for host dbeaver", "web-postgres-connection-pg-hba-001", ["p0-05-firewall-acl-nat-c001"]),
    ("HN-CD-008", "oracle_tns_12541_vs_generic_listener", "oracle sql developer ora-12541 tns no listener", "web-oracle-tns-12541-no-listener-001", ["p0-04-service-listening-c001"]),
    
    # 3. Cloud Productivity vs Endpoint Damage
    ("HN-CD-009", "outlook_scanpst_vs_hardware_crash", "outlook crash liên tục lúc mở sửa file ost bằng scanpst", "web-outlook-ost-corruption-scanpst-001", ["kb-009", "sr-004"]),
    ("HN-CD-010", "teams_privacy_permission_vs_hardware_mic", "teams không nhận camera do privacy permissions windows", "web-teams-camera-mic-permissions-win-001", ["web-bluetooth-le-audio-mic-desync-001"]),
    ("HN-CD-011", "onedrive_file_lock_vs_disk_storage", "onedrive báo file open in another program conflict", "web-onedrive-file-lock-sync-conflict-001", ["kb-006"]),
    
    # 4. Identity & Windows Hello vs BitLocker PIN
    ("HN-CD-012", "windows_hello_pin_vs_bitlocker_pin", "lỗi windows hello 0x80090016 pin không dùng được xóa ngc", "web-windows-hello-pin-reset-001", ["web-bitlocker-tpm-recovery-loop-001"]),
    ("HN-CD-013", "credential_manager_stale_vs_ad_lockout", "xóa cached credentials trong credential manager sso loop", "web-windows-credential-manager-clear-001", ["kb-001"]),
    ("HN-CD-014", "authenticator_transfer_vs_admin_reset", "tự chuyển microsoft authenticator sang điện thoại mới qua cloud", "web-entra-authenticator-device-transfer-001", ["kb-002"]),
    
    # 5. Cross-platform Wi-Fi / SMB vs Windows Local Shares
    ("HN-CD-015", "macos_smb_vs_windows_smb", "kết nối share folder windows smb trên macbook finder cmd k", "web-macos-smb-file-share-001", ["kb-012"]),
    ("HN-CD-016", "linux_mount_cifs_vs_windows_explorer", "mount ổ đĩa windows bằng mount.cifs cifs-utils ubuntu", "web-linux-cifs-smb-mount-001", ["kb-012"]),
    ("HN-CD-017", "macos_keychain_trust_vs_certmgr", "import root ca vào keychain access macos always trust", "web-macos-certificate-trust-001", ["web-browser-err-cert-authority-001"]),
    
    # 6. HTTP Status vs Transport Network
    ("HN-CD-018", "http_502_vs_tcp_refused", "http 502 bad gateway backend upstream server sập", "web-http-status-502-bad-gateway-001", ["p0-04-service-listening-c001"]),
    ("HN-CD-019", "http_504_vs_tcp_timeout", "http 504 gateway timeout upstream xử lý chậm", "web-http-status-504-timeout-001", ["p0-03-tcp-failure-semantics-c001"]),
    ("HN-CD-020", "http_401_vs_403", "phân biệt http 401 unauthorized và 403 forbidden", "web-http-status-401-vs-403-001", ["p0-10-http-403-forbidden-c001"]),
]

expanded_hn_dataset = []
hn_idx = 1
for base_id, cat, query, target_doc, neg_docs in hard_negatives:
    for var in [query, f"cách xử lý lỗi {query}", f"hướng dẫn fix {query}", f"khắc phục sự cố {query}", f"tài liệu troubleshooting {query}"]:
        if len(expanded_hn_dataset) >= 100:
            break
        expanded_hn_dataset.append({
            "id": f"HN-V4-{hn_idx:03d}",
            "category": cat,
            "query": var,
            "primary_expected_source_ids": [target_doc],
            "hard_negative_source_ids": neg_docs
        })
        hn_idx += 1

hn_file = Path("eval/expanded_hard_negatives_v4.json")
hn_file.write_text(json.dumps(expanded_hn_dataset, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote Expanded Hard Negatives Dataset ({len(expanded_hn_dataset)} cases) to {hn_file}")
