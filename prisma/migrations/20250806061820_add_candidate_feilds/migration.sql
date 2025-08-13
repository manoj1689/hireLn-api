/*
  Warnings:

  - The `previousJobs` column on the `candidates` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "candidates" ADD COLUMN     "address" TEXT[],
ADD COLUMN     "certifications" JSONB,
ADD COLUMN     "hobbies" TEXT[],
ADD COLUMN     "internship" TEXT,
ADD COLUMN     "languages" TEXT[],
ADD COLUMN     "links" TEXT[],
ADD COLUMN     "personalInfo" JSONB,
ADD COLUMN     "projects" JSONB,
ADD COLUMN     "softSkills" TEXT[],
ADD COLUMN     "summary" TEXT,
ADD COLUMN     "technicalSkills" TEXT[],
DROP COLUMN "previousJobs",
ADD COLUMN     "previousJobs" JSONB;
