/*
  Warnings:

  - You are about to drop the column `internship` on the `candidates` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "candidates" DROP COLUMN "internship",
ADD COLUMN     "internships" TEXT;
