/*
  Warnings:

  - The `experience` column on the `candidates` table would be dropped and recreated. This will lead to data loss if there is data in the column.
  - The `education` column on the `candidates` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "candidates" DROP COLUMN "experience",
ADD COLUMN     "experience" JSONB,
DROP COLUMN "education",
ADD COLUMN     "education" JSONB;
