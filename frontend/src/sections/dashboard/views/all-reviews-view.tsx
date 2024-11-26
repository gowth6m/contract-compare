import { useState } from 'react';
import { paths } from '@/routes/paths';
import { useQuery } from 'react-query';
import { useRouter } from '@/routes/hooks';
import ApiClient from '@/services/api-client';
import { LoadingTopbar } from '@/components/loading-screen';
import CustomBreadcrumbs from '@/components/custom-breadcrumbs';

import { Alert, Stack, Button } from '@mui/material';

import FileRecentItem from '../components/file-recent-item';

// ----------------------------------------------------------------------

const AllReviewsView = () => {
  const router = useRouter();

  const [filesToCompare, setFilesToCompare] = useState<string[]>([]);

  const allReviewsQuery = useQuery({
    queryKey: ['getAllReviews'],
    queryFn: async () => {
      return await ApiClient.contract.getAllReviews({});
    },
  });

  const handleToggleFileToCompare = (fileId: string) => {
    if (filesToCompare.includes(fileId)) {
      setFilesToCompare(filesToCompare.filter((file) => file !== fileId));
    } else {
      setFilesToCompare([...filesToCompare, fileId]);
    }
  };

  const renderHeader = (
    <CustomBreadcrumbs
      heading="All Reviews"
      links={[
        {
          name: 'Dashboard',
          href: paths.DASHBOARD.INDEX,
        },
        { name: 'Reviews' },
      ]}
      sx={{
        mb: 3,
      }}
      actions={[
        <>
          {filesToCompare.length > 1 && (
            <Button
              size="small"
              variant="contained"
              onClick={() => {
                console.log('Comparing files:', filesToCompare);
                router.push(`/dashboard/contract/compare?ids=${filesToCompare.join(',')}`);
              }}
            >
              Compare {filesToCompare.length} files
            </Button>
          )}
        </>,
      ]}
    />
  );

  return (
    <div>
      {allReviewsQuery.isLoading && <LoadingTopbar />}

      {renderHeader}

      {allReviewsQuery.isLoading ? (
        <Alert severity="info">Loading...</Alert>
      ) : allReviewsQuery.isError ? (
        <Alert severity="error">Error loading history</Alert>
      ) : !allReviewsQuery?.data?.data?.length ? (
        <Alert severity="info">No contracts found</Alert>
      ) : (
        <Stack spacing={2}>
          {allReviewsQuery?.data?.data?.map((file) => (
            <FileRecentItem
              key={file._id}
              file={file}
              checked={filesToCompare.includes(file._id)}
              onClick={() => {
                handleToggleFileToCompare(file._id);
              }}
            />
          ))}
        </Stack>
      )}
    </div>
  );
};

export default AllReviewsView;
