-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Host: mysql-fabianmedina.alwaysdata.net
-- Generation Time: Jan 28, 2026 at 08:29 PM
-- Server version: 10.11.15-MariaDB
-- PHP Version: 8.4.16

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `fabianmedina_miapp`
--

-- --------------------------------------------------------

--
-- Table structure for table `cliente`
--

CREATE TABLE `cliente` (
  `id_cliente` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `direccion` varchar(150) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `cliente`
--

INSERT INTO `cliente` (`id_cliente`, `nombre`, `telefono`, `email`, `direccion`) VALUES
(1, 'Fabian Medina', NULL, 'fabianmedina449@gmail.com', NULL),
(2, 'Juan Lopez', NULL, 'juan@pruebas.com', NULL),
(3, 'Ana María Vaca Rodríguez ', NULL, 'anamariavz@outlook.com', NULL),
(4, 'Edier E', NULL, 'espinosaedier@unbosque.edu.co', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `cliente_promocion`
--

CREATE TABLE `cliente_promocion` (
  `id_cliente` int(11) NOT NULL,
  `id_promocion` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `codigo_barras`
--

CREATE TABLE `codigo_barras` (
  `id_codigo` int(11) NOT NULL,
  `tipo` varchar(50) NOT NULL,
  `codigo` varchar(100) NOT NULL,
  `id_prenda` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `historial_operaciones`
--

CREATE TABLE `historial_operaciones` (
  `id_operacion` int(11) NOT NULL,
  `accion` varchar(255) NOT NULL,
  `fecha` date NOT NULL,
  `id_usuario` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `imagen`
--

CREATE TABLE `imagen` (
  `id_imagen` int(11) NOT NULL,
  `url_imagen` varchar(255) NOT NULL,
  `id_pedido` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `pedido`
--

CREATE TABLE `pedido` (
  `id_pedido` int(11) NOT NULL,
  `fecha_ingreso` date NOT NULL,
  `fecha_entrega` date DEFAULT NULL,
  `estado` varchar(50) NOT NULL,
  `id_cliente` int(11) NOT NULL,
  `codigo_barras` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `pedido`
-- Tabla vacía después de migración
--

--
-- Table structure for table `prenda`
--

CREATE TABLE `prenda` (
  `id_prenda` int(11) NOT NULL,
  `tipo` varchar(50) NOT NULL,
  `descripcion` varchar(150) DEFAULT NULL,
  `observaciones` varchar(255) DEFAULT NULL,
  `id_pedido` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `prenda`
--

INSERT INTO `prenda` (`id_prenda`, `tipo`, `descripcion`, `observaciones`, `id_pedido`) VALUES
(1, 'A', 'Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba', 'Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba Prueba', 1),
(2, 'B', 'Prueba 2 Prueba 2 Prueba 2 Prueba 2', 'Prueba 2', 1);

-- --------------------------------------------------------

--
-- Table structure for table `promocion`
--

CREATE TABLE `promocion` (
  `id_promocion` int(11) NOT NULL,
  `descripcion` varchar(200) NOT NULL,
  `descuento` float NOT NULL,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `recibo`
--

CREATE TABLE `recibo` (
  `id_recibo` int(11) NOT NULL,
  `id_pedido` int(11) NOT NULL,
  `id_cliente` int(11) NOT NULL,
  `monto` decimal(10,2) NOT NULL,
  `fecha` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `recibo`
--

INSERT INTO `recibo` (`id_recibo`, `id_pedido`, `id_cliente`, `monto`, `fecha`) VALUES
(1, 1, 3, 0.00, '2025-10-29 04:47:14');

-- --------------------------------------------------------

--
-- Table structure for table `reporte`
--

CREATE TABLE `reporte` (
  `id_reporte` int(11) NOT NULL,
  `tipo` varchar(50) NOT NULL,
  `fecha_generacion` date NOT NULL,
  `id_pedido` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `usuario`
--

CREATE TABLE `usuario` (
  `id_usuario` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `rol` varchar(50) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `usuario`
--

INSERT INTO `usuario` (`id_usuario`, `nombre`, `rol`, `email`, `username`, `password`) VALUES
(3, 'Fabian Medina', 'cliente', 'fabianmedina449@gmail.com', 'fmedinac', 'scrypt:32768:8:1$KxsiZll0m3uUmo6G$a1a839fedb7e3f044e9b7ad35090cd49661c2d034b8f25032168c890c1854e32936c10f884d6ceb166c74611c8abcc8ae695c4e843df3980c6ea25f04bbeef30'),
(5, 'Fabian Medina', 'cliente', 'fabianmedina449@gmail.com', 'fmedinac1', 'scrypt:32768:8:1$3XEAcdW0jyzBgyeJ$ed7430110f790b248e097547f29a8a3c7e82fea330726969ffef89277039c3ba285174c50078264df7ef413c7b14273e9eb850cb3e53f105116f7e158c96cd11'),
(6, 'Juan Niño', 'cliente', 'jdninom@unbosque.edu.co', 'Jdninom', 'scrypt:32768:8:1$xlGclmz7YcN1SAiZ$86380cf97154030c51956a338a93bafca11562ac3a94f7cea218bd25d5708eddd20a569d040627c7e89dc349fe8a493cce2727f622adc7500b634df22937a399'),
(7, 'Fabian Medina', 'cliente', 'fmedinac@unbosque.edu.co', 'fmedinac2', 'scrypt:32768:8:1$qotma3iuj9pNUnG9$e11c25d9d4bded8fb09f66af7520168aae6fdc1db9c2f7060119448191ad78bf08c4665cf2999425113fd1b252c5f051d39647ca191e034192b5cc819c1c27d7'),
(8, 'CHristian', 'cliente', 'Cagomezg@unbosque.edu.co', 'Cagomez', 'scrypt:32768:8:1$jhLOAawrq8WeC7hl$40b647c0e192cb1121a197b01e050565e251c16a5ee2f658fcde52acefbc14d1978978b56be3dfc5ffdb792ed6c073a512a88822685c1e48c2d72cf8c88c4bec'),
(9, 'Fabian Medina', 'cliente', 'fabianmedina449@gmail.com', 'fmedinac4', 'scrypt:32768:8:1$5HVMg7c15GdLKf6t$7a4b8e7b3358c584020abae39b1b6c568366067086b0e8f2be7fa726602df0ed80a4b8e27555f2826e5f91d3d13accab17373b3313103c6a5344ed3e5d7a4b4e'),
(12, 'Juan', 'cliente', 'victorjcast7@gmail.com', 'JuanDa', 'scrypt:32768:8:1$cojrmzoIhjLPL7UB$90a78bb4ecfe5fee78df01270d4932ca28d37b5d58c01a2b3452f7f9212e258dac390dad5f713f71c17c29b85348a6416709fccbad7680215d777dc61fd3a384'),
(15, 'Fabian Medina', 'administrador', 'fabianm@lavanderia.com', 'fabianm', 'scrypt:32768:8:1$AkRP2VEEbqrWiqcP$665e5111d822c1c1a297dc98aedb2ce868f5527eb5954369493c20959a5897f0791f2361f0b02a60973bde4420b7b636f4f189ffc2b3cb22aa4ec22048536321'),
(16, 'Juan Nino', 'administrador', 'juannino@lavanderia.com', 'juannino', 'scrypt:32768:8:1$VvkPoYOCEayHegpt$a8a32deb90199724dce2dabcbe74820129c42d8cdbeac946ca92bbca2ccb7e790dc1a842be9f7474cf7b7d4f769a2566fb642dfabd2846005658687ebc4a8fe3'),
(17, 'Sergio', 'cliente', 'fabianmedina449@gmail.com', 'sergiolin', 'scrypt:32768:8:1$iiHjbzP4Ryut2JFc$8d6417bb113e47f8951aac23ec39da3d491a070a5204eba1e005739968794e4324c24e17e8a6c0d4a62ecef4dc76f1b4d22f1c8430e7bece1dda261476bf9f76'),
(20, 'Santiago', 'cliente', 'proyectogradoserio@gmail.com', 'SantiG', 'scrypt:32768:8:1$7dOjcy04Ix8lZB6g$33a5232299ab271bb29de567df1b9fa112d7b2e0d3db4f8d47c7058c3621a7b674f94ef52f9f2bc6863a3c49f39b8e46f94cf657fe55ad7bd377a8f2f9bce1a0'),
(21, 'Juan Lopez', 'cliente', 'juan@pruebas.com', 'Juan', 'scrypt:32768:8:1$PSjdcSTHDw48YgwI$8403798297aeff26dfae32f893c3d0e8c0178d93411faac6222bc311aa6ca53d234e751a2dd0ca08e43b0e0cae244e7413698cfd993db66f0b3e0eb603bf3528'),
(25, 'Ana María Vaca Rodríguez ', 'cliente', 'anamariavz@outlook.com', 'Anamaria04', 'scrypt:32768:8:1$f32oFFSMdH0xAOg6$04c71319766d0723c54a5517bb7883db0db4c2368dc0d1d6591975e6ef3492c987d18a790ca9415a5f2fa2bcbd5f8e3901bda82926dbb03e80211a5b5f8aa079'),
(26, 'loliano', 'cliente', 'lolianod@gmail.com', 'lolianod', 'scrypt:32768:8:1$V9qiGfyWgKWyxTld$9e55e750fe87c0bf985e73ff40db6872f2ff7ea3bbd73f7c085db99a3e269a42d971cf2f01c31a46fa187383012dd2471231ac9dd538bd1715dde4fb27fea5c3'),
(27, 'Edier E', 'cliente', 'espinosaedier@unbosque.edu.co', 'Edier', 'scrypt:32768:8:1$eJ5lFo3diGtelhdR$4ac2a5ffc0a5bebf671f2769501de696ac2fb1d7fabb6ce5305f2fd161ae6d10614d6930a2c6321d04f7dd83856839bc87f852264cf9571a149e234ac7ed859e');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `cliente`
--
ALTER TABLE `cliente`
  ADD PRIMARY KEY (`id_cliente`);

--
-- Indexes for table `cliente_promocion`
--
ALTER TABLE `cliente_promocion`
  ADD PRIMARY KEY (`id_cliente`,`id_promocion`),
  ADD KEY `fk_cliente_promocion_promocion` (`id_promocion`);

--
-- Indexes for table `codigo_barras`
--
ALTER TABLE `codigo_barras`
  ADD PRIMARY KEY (`id_codigo`),
  ADD KEY `fk_codigo_prenda` (`id_prenda`);

--
-- Indexes for table `historial_operaciones`
--
ALTER TABLE `historial_operaciones`
  ADD PRIMARY KEY (`id_operacion`),
  ADD KEY `fk_historial_usuario` (`id_usuario`);

--
-- Indexes for table `imagen`
--
ALTER TABLE `imagen`
  ADD PRIMARY KEY (`id_imagen`),
  ADD KEY `fk_imagen_pedido` (`id_pedido`);

--
-- Indexes for table `pedido`
--
ALTER TABLE `pedido`
  ADD PRIMARY KEY (`id_pedido`),
  ADD UNIQUE KEY `codigo_barras` (`codigo_barras`),
  ADD KEY `fk_pedido_cliente` (`id_cliente`);

--
-- Indexes for table `prenda`
--
ALTER TABLE `prenda`
  ADD PRIMARY KEY (`id_prenda`),
  ADD KEY `fk_prenda_pedido` (`id_pedido`);

--
-- Indexes for table `promocion`
--
ALTER TABLE `promocion`
  ADD PRIMARY KEY (`id_promocion`);

--
-- Indexes for table `recibo`
--
ALTER TABLE `recibo`
  ADD PRIMARY KEY (`id_recibo`),
  ADD KEY `id_pedido` (`id_pedido`),
  ADD KEY `id_cliente` (`id_cliente`);

--
-- Indexes for table `reporte`
--
ALTER TABLE `reporte`
  ADD PRIMARY KEY (`id_reporte`),
  ADD KEY `fk_reporte_pedido` (`id_pedido`);

--
-- Indexes for table `usuario`
--
ALTER TABLE `usuario`
  ADD PRIMARY KEY (`id_usuario`),
  ADD UNIQUE KEY `username` (`username`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `cliente`
--
ALTER TABLE `cliente`
  MODIFY `id_cliente` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `codigo_barras`
--
ALTER TABLE `codigo_barras`
  MODIFY `id_codigo` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `historial_operaciones`
--
ALTER TABLE `historial_operaciones`
  MODIFY `id_operacion` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `imagen`
--
ALTER TABLE `imagen`
  MODIFY `id_imagen` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `pedido`
--
ALTER TABLE `pedido`
  MODIFY `id_pedido` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `prenda`
--
ALTER TABLE `prenda`
  MODIFY `id_prenda` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `promocion`
--
ALTER TABLE `promocion`
  MODIFY `id_promocion` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `recibo`
--
ALTER TABLE `recibo`
  MODIFY `id_recibo` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `reporte`
--
ALTER TABLE `reporte`
  MODIFY `id_reporte` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `usuario`
--
ALTER TABLE `usuario`
  MODIFY `id_usuario` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=28;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `cliente_promocion`
--
ALTER TABLE `cliente_promocion`
  ADD CONSTRAINT `fk_cliente_promocion_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `cliente` (`id_cliente`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_cliente_promocion_promocion` FOREIGN KEY (`id_promocion`) REFERENCES `promocion` (`id_promocion`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `codigo_barras`
--
ALTER TABLE `codigo_barras`
  ADD CONSTRAINT `fk_codigo_prenda` FOREIGN KEY (`id_prenda`) REFERENCES `prenda` (`id_prenda`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `historial_operaciones`
--
ALTER TABLE `historial_operaciones`
  ADD CONSTRAINT `fk_historial_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `imagen`
--
ALTER TABLE `imagen`
  ADD CONSTRAINT `fk_imagen_pedido` FOREIGN KEY (`id_pedido`) REFERENCES `pedido` (`id_pedido`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `pedido`
--
ALTER TABLE `pedido`
  ADD CONSTRAINT `fk_pedido_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `cliente` (`id_cliente`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `prenda`
--
ALTER TABLE `prenda`
  ADD CONSTRAINT `fk_prenda_pedido` FOREIGN KEY (`id_pedido`) REFERENCES `pedido` (`id_pedido`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `recibo`
--
ALTER TABLE `recibo`
  ADD CONSTRAINT `recibo_ibfk_1` FOREIGN KEY (`id_pedido`) REFERENCES `pedido` (`id_pedido`),
  ADD CONSTRAINT `recibo_ibfk_2` FOREIGN KEY (`id_cliente`) REFERENCES `usuario` (`id_usuario`);

--
-- Constraints for table `reporte`
--
ALTER TABLE `reporte`
  ADD CONSTRAINT `fk_reporte_pedido` FOREIGN KEY (`id_pedido`) REFERENCES `pedido` (`id_pedido`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
