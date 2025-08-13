/*
  Warnings:

  - The `internships` column on the `candidates` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "candidates" DROP COLUMN "internships",
ADD COLUMN     "internships" TEXT[];
