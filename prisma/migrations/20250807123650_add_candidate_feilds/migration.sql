/*
  Warnings:

  - You are about to drop the column `educationField` on the `candidates` table. All the data in the column will be lost.
  - You are about to drop the column `experienceSummary` on the `candidates` table. All the data in the column will be lost.
  - You are about to drop the column `links` on the `candidates` table. All the data in the column will be lost.
  - You are about to drop the column `skills` on the `candidates` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "candidates" DROP COLUMN "educationField",
DROP COLUMN "experienceSummary",
DROP COLUMN "links",
DROP COLUMN "skills";
