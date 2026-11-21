-- Migration auth Google-only. Chạy một lần trên database hiện tại.
ALTER TABLE `NguoiDung`
  MODIFY COLUMN `VaiTro` ENUM('Admin', 'Farmer', 'User') NOT NULL DEFAULT 'Farmer',
  ADD COLUMN `IsVerified` TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN `HoTen` VARCHAR(200) DEFAULT NULL,
  ADD COLUMN `GoogleId` VARCHAR(255) DEFAULT NULL,
  ADD COLUMN `AnhDaiDien` VARCHAR(1000) DEFAULT NULL,
  ADD UNIQUE KEY `uq_nguoidung_google_id` (`GoogleId`);

-- Các tài khoản seed cũ đã được tạo sẵn, không cần OTP lần đầu.
UPDATE `NguoiDung` SET `IsVerified` = 1 WHERE `IsVerified` = 0;

DROP TABLE IF EXISTS `OTP_Verification`;
