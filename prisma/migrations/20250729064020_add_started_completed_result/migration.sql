/*
  Warnings:

  - The `candidateSkills` column on the `interviews` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "interviews" DROP COLUMN "candidateSkills",
ADD COLUMN     "candidateSkills" TEXT[];
