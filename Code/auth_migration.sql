-- Chạy một lần trên database hiện tại trước khi bật Auth mới.
ALTER TABLE `NguoiDung`
  MODIFY COLUMN `VaiTro` ENUM('Admin', 'Farmer', 'User') NOT NULL DEFAULT 'Farmer',
  ADD COLUMN `IsVerified` TINYINT(1) NOT NULL DEFAULT 0;

-- Các tài khoản seed cũ đã được tạo sẵn, không cần OTP lần đầu.
UPDATE `NguoiDung` SET `IsVerified` = 1 WHERE `IsVerified` = 0;

CREATE TABLE `OTP_Verification` (
  `Id` INT NOT NULL AUTO_INCREMENT,
  `MaNguoiDung` INT NOT NULL,
  `MaOTP` VARCHAR(255) NOT NULL,
  `HetHanLuc` DATETIME NOT NULL,
  `DaSuDung` TINYINT(1) NOT NULL DEFAULT 0,
  `NgayTao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`Id`),
  KEY `idx_otp_user_created` (`MaNguoiDung`, `NgayTao`),
  CONSTRAINT `fk_otp_nguoidung`
    FOREIGN KEY (`MaNguoiDung`) REFERENCES `NguoiDung` (`MaNguoiDung`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
