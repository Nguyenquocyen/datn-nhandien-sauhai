CREATE DATABASE IF NOT EXISTS `nhandien_sauhai_db`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `nhandien_sauhai_db`;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `OTP_Verification`;
DROP TABLE IF EXISTS `tinnhanchat`;
DROP TABLE IF EXISTS `ketquadss`;
DROP TABLE IF EXISTS `ketquanhandien`;
DROP TABLE IF EXISTS `sosanhcapahp`;
DROP TABLE IF EXISTS `trongsoahp`;
DROP TABLE IF EXISTS `lichsucanhtac`;
DROP TABLE IF EXISTS `phienphantich`;
DROP TABLE IF EXISTS `sauhai_giaiphap`;
DROP TABLE IF EXISTS `luongchat`;
DROP TABLE IF EXISTS `cauhinhahp`;
DROP TABLE IF EXISTS `giaiphapsinhhoc`;
DROP TABLE IF EXISTS `sauhai`;
DROP TABLE IF EXISTS `nguoidung`;
DROP TABLE IF EXISTS `tieuchiahp`;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE `NguoiDung` (
  `MaNguoiDung` INT NOT NULL AUTO_INCREMENT,
  `TenDangNhap` VARCHAR(100) NOT NULL,
  `Email` VARCHAR(255) NOT NULL,
  `MatKhauHash` VARCHAR(255) NOT NULL,
  `VaiTro` ENUM('Admin', 'Farmer', 'User') NOT NULL DEFAULT 'Farmer',
  `IsVerified` TINYINT(1) NOT NULL DEFAULT 0,
  `NgayTao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaNguoiDung`),
  UNIQUE KEY `uq_nguoidung_tendangnhap` (`TenDangNhap`),
  UNIQUE KEY `uq_nguoidung_email` (`Email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE `SauHai` (
  `MaSauHai` INT NOT NULL AUTO_INCREMENT,
  `TenTiengViet` VARCHAR(100) NOT NULL,
  `TenKhoaHoc` VARCHAR(150) DEFAULT NULL,
  `MaLopYOLO` VARCHAR(50) NOT NULL,
  `VongDoi` TEXT DEFAULT NULL,
  `DacDiemHinhThai` TEXT DEFAULT NULL,
  `CachThucGayHai` TEXT DEFAULT NULL,
  `MucDoGayHai` TEXT DEFAULT NULL,
  `TrieuChungGayHai` TEXT DEFAULT NULL,
  `ThuVienAnh_JSON` JSON DEFAULT NULL,
  `VungPhanBo_JSON` JSON DEFAULT NULL,
  `CayTrongBiHai_JSON` JSON DEFAULT NULL,
  PRIMARY KEY (`MaSauHai`),
  UNIQUE KEY `uq_sauhai_malopyolo` (`MaLopYOLO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `GiaiPhapSinhHoc` (
  `MaGiaiPhap` INT NOT NULL AUTO_INCREMENT,
  `TenGiaiPhap` VARCHAR(255) NOT NULL,
  `ChiPhiMoiHecta` DECIMAL(12,2) DEFAULT NULL,
  `SoNgayHieuQua` INT DEFAULT NULL,
  `DiemAnToanMoiTruong` DECIMAL(5,2) DEFAULT NULL,
  `PhuongPhapApDung` TEXT DEFAULT NULL,
  `score_mat_do` FLOAT DEFAULT NULL,
  `score_chi_phi` FLOAT DEFAULT NULL,
  `score_thoi_gian` FLOAT DEFAULT NULL,
  `score_an_toan` FLOAT DEFAULT NULL,
  `mo_ta` TEXT DEFAULT NULL,
  `cach_su_dung` TEXT DEFAULT NULL,
  `luu_y_khi_dung` TEXT DEFAULT NULL,
  `co_so_khoa_hoc` TEXT DEFAULT NULL,
  PRIMARY KEY (`MaGiaiPhap`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `CauHinhDSS` (
  `MaCauHinh` INT NOT NULL AUTO_INCREMENT,
  `TenCauHinh` VARCHAR(150) NOT NULL,
  `MaTranSoSanh_JSON` JSON DEFAULT NULL,
  `TrongSo_JSON` JSON DEFAULT NULL,
  `NgayTao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaCauHinh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `SauHai_GiaiPhap` (
  `MaLienKet` INT NOT NULL AUTO_INCREMENT,
  `MaSauHai` INT NOT NULL,
  `MaGiaiPhap` INT NOT NULL,
  `DiemHieuQua` DECIMAL(5,2) DEFAULT NULL,
  PRIMARY KEY (`MaLienKet`),
  UNIQUE KEY `uq_sauhai_giaiphap` (`MaSauHai`, `MaGiaiPhap`),
  CONSTRAINT `fk_shgp_sauhai`
    FOREIGN KEY (`MaSauHai`) REFERENCES `SauHai` (`MaSauHai`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_shgp_giaiphap`
    FOREIGN KEY (`MaGiaiPhap`) REFERENCES `GiaiPhapSinhHoc` (`MaGiaiPhap`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `LichSuCanhTac` (
  `MaLichSu` INT NOT NULL AUTO_INCREMENT,
  `MaSauHai` INT NOT NULL,
  `GiaiDoanLua` ENUM(
    'ma',
    'de_nhanh',
    'lam_dong',
    'tro_bong',
    'chin'
  ) NOT NULL,
  `MuaVu` ENUM(
    'dong_xuan',
    'he_thu',
    'thu_dong'
  ) NOT NULL,
  `VungMien` ENUM(
    'dbscl',
    'dong_nam_bo',
    'tay_nguyen',
    'dbsh',
    'bac_trung_bo',
    'duyen_hai_mien_trung'
  ) NOT NULL,
  `NhietDo` DECIMAL(4,1) NOT NULL,
  `DoAm` DECIMAL(4,1) NOT NULL,
  `MatDo` FLOAT NOT NULL DEFAULT 1.0,
  `DiemHieuQua` FLOAT NOT NULL DEFAULT 0.0,
  `NguonTrichDan` VARCHAR(1000) DEFAULT NULL,
  `GhiChuTrichDan` TEXT DEFAULT NULL,
  `MaGiaiPhapDaChon` INT DEFAULT NULL,
  `KetQua` ENUM(
    'tot',
    'trung_binh',
    'kem',
    'chua_danh_gia'
  ) NOT NULL DEFAULT 'chua_danh_gia',
  PRIMARY KEY (`MaLichSu`),
  CONSTRAINT `fk_lichsu_sauhai`
    FOREIGN KEY (`MaSauHai`) REFERENCES `SauHai` (`MaSauHai`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_lichsu_giaiphap`
    FOREIGN KEY (`MaGiaiPhapDaChon`)
    REFERENCES `GiaiPhapSinhHoc` (`MaGiaiPhap`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `PhienPhanTich` (
  `MaPhien` INT NOT NULL AUTO_INCREMENT,
  `MaNguoiDung` INT DEFAULT NULL,
  `DuongDanAnhGoc` VARCHAR(500) NOT NULL,
  `DuongDanAnhKetQua` VARCHAR(500) DEFAULT NULL,
  `QuyMoDienTich` VARCHAR(100) DEFAULT NULL,
  `NhietDo` DECIMAL(4,1) DEFAULT NULL,
  `DoAm` DECIMAL(4,1) DEFAULT NULL,
  `KetQuaAI_JSON` JSON DEFAULT NULL,
  `KetQuaDSS_JSON` JSON DEFAULT NULL,
  `NgayTao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaPhien`),
  CONSTRAINT `fk_phien_nguoidung`
    FOREIGN KEY (`MaNguoiDung`) REFERENCES `NguoiDung` (`MaNguoiDung`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `LuongChat` (
  `MaLuong` INT NOT NULL AUTO_INCREMENT,
  `MaNguoiDung` INT NOT NULL,
  `TenLuong` VARCHAR(255) NOT NULL,
  `NgayTao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaLuong`),
  CONSTRAINT `fk_luong_nguoidung`
    FOREIGN KEY (`MaNguoiDung`) REFERENCES `NguoiDung` (`MaNguoiDung`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `TinNhanChat` (
  `MaTinNhan` INT NOT NULL AUTO_INCREMENT,
  `MaLuong` INT NOT NULL,
  `MaPhien_Context` INT DEFAULT NULL,
  `VaiTro` ENUM('User', 'AI') NOT NULL,
  `NoiDung` TEXT NOT NULL,
  `NgayTao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaTinNhan`),
  CONSTRAINT `fk_tinnhan_luong`
    FOREIGN KEY (`MaLuong`) REFERENCES `LuongChat` (`MaLuong`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_tinnhan_phien_context`
    FOREIGN KEY (`MaPhien_Context`) REFERENCES `PhienPhanTich` (`MaPhien`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
