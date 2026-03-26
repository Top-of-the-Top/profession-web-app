param([Parameter(Mandatory)][string]$FeatureName)

$featurePath = "src/features/$FeatureName"

New-Item -ItemType Directory -Force -Path "$featurePath/model/store", "$featurePath/model/lib", "$featurePath/ui/CourseBuilder", "$featurePath/api", "$featurePath/lib" | Out-Null

@"
export * from './store';
export * from './types';
"@ | Out-File -FilePath "$featurePath/model/index.ts" -Encoding utf8

@"
export { CourseBuilder } from './CourseBuilder';
"@ | Out-File -FilePath "$featurePath/ui/index.ts" -Encoding utf8
@"
export { CourseBuilder } from './CourseBuilder';
"@ | Out-File -FilePath "$featurePath/ui/CourseBuilder/index.tsx" -Encoding utf8

@"
export * from './model';
export * from './ui';
export * from './api';
"@ | Out-File -FilePath "$featurePath/index.ts" -Encoding utf8

New-Item -ItemType File -Force -Path @(
    "$featurePath/model/store.ts",
    "$featurePath/model/types.ts", 
    "$featurePath/ui/CourseBuilder/CourseBuilder.tsx",
    "$featurePath/ui/CourseBuilder/CourseBuilder.module.css",
    "$featurePath/api/courseBuilderApi.ts",
    "$featurePath/lib/constants.ts"
)

Write-Host "Feature '$FeatureName' created at $featurePath" -ForegroundColor Green
