/*
  Warnings:

  - A unique constraint covering the columns `[applicationId]` on the table `interview_results` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `applicationId` to the `interview_results` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "interview_results" ADD COLUMN     "applicationId" TEXT NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "interview_results_applicationId_key" ON "interview_results"("applicationId");

-- AddForeignKey
ALTER TABLE "interview_results" ADD CONSTRAINT "interview_results_applicationId_fkey" FOREIGN KEY ("applicationId") REFERENCES "applications"("id") ON DELETE CASCADE ON UPDATE CASCADE;
