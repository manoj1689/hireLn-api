/*
  Warnings:

  - The `candidateEducation` column on the `interviews` table would be dropped and recreated. This will lead to data loss if there is data in the column.
  - The `candidateExperience` column on the `interviews` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "interviews" DROP COLUMN "candidateEducation",
ADD COLUMN     "candidateEducation" JSONB,
DROP COLUMN "candidateExperience",
ADD COLUMN     "candidateExperience" JSONB;
