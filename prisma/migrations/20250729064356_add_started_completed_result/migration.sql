/*
  Warnings:

  - The `jobCertificates` column on the `interviews` table would be dropped and recreated. This will lead to data loss if there is data in the column.
  - The `jobResponsibility` column on the `interviews` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "interviews" DROP COLUMN "jobCertificates",
ADD COLUMN     "jobCertificates" TEXT[],
DROP COLUMN "jobResponsibility",
ADD COLUMN     "jobResponsibility" TEXT[];
