import Row from '@/components/core/row';
import { useRouter } from '@/routes/hooks';
import { Upload } from '@/components/upload';
import Column from '@/components/core/column';
import ApiClient from '@/services/api-client';
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { useSnackbar } from '@/components/snackbar';
import { LoadingTopbar } from '@/components/loading-screen';

import { Alert, Stack, Button, Typography } from '@mui/material';

import FileRecentItem from '../components/file-recent-item';

// --------------------------------------------------

const DashboardIndexView = () => {
  const router = useRouter();

  const { enqueueSnackbar } = useSnackbar();

  const [files, setFiles] = useState<File[]>([]);

  const [filesToCompare, setFilesToCompare] = useState<string[]>([]);

  const [pollingEnabled, setPollingEnabled] = useState(false);

  const [pollingStartTime, setPollingStartTime] = useState<number | null>(null);

  // ------------ UTILS ------------

  const calculateRefetchInterval = () => {
    if (!pollingStartTime) return false;

    const elapsed = Date.now() - pollingStartTime;

    if (elapsed > 2 * 60 * 1000) return false; // Stop polling after 2 min

    // Exponential backoff intervals: 2s, 5s, 10s, 20s
    if (elapsed < 10 * 1000) return 2000;
    if (elapsed < 30 * 1000) return 5000;
    if (elapsed < 60 * 1000) return 10000;
    return 20000;
  };

  // ------------ QUERIES ---------------

  const recentQuery = useQuery({
    queryKey: ['getAllReviews', { page: 1, limit: 10 }],
    queryFn: async () => {
      return await ApiClient.contract.getAllReviews({
        page: 1,
        limit: 10,
      });
    },
    refetchInterval: pollingEnabled ? calculateRefetchInterval() : false, // polling at 10s interval (TODO: use websockets or web hook)
    refetchIntervalInBackground: false,
  });

  // ------------ MUTATIONS ------------

  const uploadFileMutation = useMutation({
    mutationFn: async (files: File[]) => {
      return await ApiClient.contract.upload({ files });
    },
    onError: () => {
      enqueueSnackbar('Error uploading files', { variant: 'error' });
      setFiles([]);
    },
    onSuccess: (res) => {
      console.info('File uploaded', res);
      setFiles([]);
      enqueueSnackbar('File sent to be processed', { variant: 'success' });
      setPollingEnabled(true);
      setPollingStartTime(Date.now());
    },
  });

  // ------------ HANDLERS ------------

  const handleDropMultiFile = useCallback(
    (acceptedFiles: File[]) => {
      setFiles([
        ...files,
        ...acceptedFiles.map((newFile) =>
          Object.assign(newFile, {
            preview: URL.createObjectURL(newFile),
          })
        ),
      ]);
      if (acceptedFiles.length) {
        uploadFileMutation.mutate(acceptedFiles);
      }
    },
    [files, uploadFileMutation]
  );

  const handleRemoveFile = (inputFile: File | string) => {
    const filesFiltered = files.filter((fileFiltered) => fileFiltered !== inputFile);
    setFiles(filesFiltered);
  };

  const handleRemoveAllFiles = () => {
    setFiles([]);
  };

  const handleToggleFileToCompare = (fileId: string) => {
    if (filesToCompare.includes(fileId)) {
      setFilesToCompare(filesToCompare.filter((file) => file !== fileId));
    } else {
      setFilesToCompare([...filesToCompare, fileId]);
    }
  };

  // ------------ RENDER ------------

  return (
    <Column>
      {recentQuery.isLoading && <LoadingTopbar />}

      <Typography variant="h5">Dashboard</Typography>

      <Upload
        multiple
        files={files}
        onDrop={handleDropMultiFile}
        onRemove={handleRemoveFile}
        onRemoveAll={handleRemoveAllFiles}
        accept={{
          'application/pdf': ['.pdf'],
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        }}
      />

      <Row justifyContent={'space-between'} alignItems={'center'}>
        <Typography variant="h5">Recent</Typography>

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
      </Row>

      {recentQuery.isLoading ? (
        <Alert severity="info">Loading...</Alert>
      ) : recentQuery.isError ? (
        <Alert severity="error">Error loading history</Alert>
      ) : !recentQuery?.data?.data?.length ? (
        <Alert severity="info">No contracts found</Alert>
      ) : (
        <Stack spacing={2}>
          {recentQuery?.data?.data?.map((file) => (
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
    </Column>
  );
};

export default DashboardIndexView;
