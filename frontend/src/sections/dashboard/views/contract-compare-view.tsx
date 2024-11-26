import { useState } from 'react';
import { useQuery } from 'react-query';
import { paths } from '@/routes/paths';
import Column from '@/components/core/column';
import ApiClient from '@/services/api-client';
import Scrollbar from '@/components/scrollbar';
import { useSearchParams } from '@/routes/hooks';
import { TableHeadCustom } from '@/components/table';
import { snakeCaseToTitleCase } from '@/utils/format';
import { ContractReview } from '@/services/types/contract';
import { LoadingTopbar } from '@/components/loading-screen';
import CustomBreadcrumbs from '@/components/custom-breadcrumbs';

import {
  Box,
  Card,
  Table,
  Button,
  Dialog,
  TableRow,
  TableBody,
  TableCell,
  Typography,
  DialogActions,
  DialogContent,
  TableContainer,
} from '@mui/material';

// --------------------------------------------------

const ContractCompareView = () => {
  const searchParams = useSearchParams();

  const ids = searchParams.get('ids')?.split(',') || [];

  const [selectedFile, setSelectedFile] = useState<ContractReview | null>(null);

  // ------------ QUERY -------------

  const contractQuery = useQuery({
    queryKey: ['compare', { ids }],
    queryFn: async () => {
      return await ApiClient.contract.compare(ids);
    },
  });

  // ------------ RENDER ------------

  const listOfLabelsForFiles = [
    {
      id: 'file_name',
      label: 'Contract',
      align: 'left',
    },
    {
      id: 'contract_type',
      label: 'Contract Type',
      align: 'left',
    },
    {
      id: 'pages',
      label: 'Number of pages',
      align: 'left',
    },
    ...Object.entries(contractQuery?.data?.data?.[0]?.properties || {}).map(([key, _value]) => ({
      id: key,
      label: snakeCaseToTitleCase(key),
      align: 'left',
    })),
  ];

  const renderHeader = (
    <CustomBreadcrumbs
      heading="Compare Contracts"
      links={[
        {
          name: 'Dashboard',
          href: paths.DASHBOARD.INDEX,
        },
        { name: 'Compare' },
      ]}
    />
  );

  const renderLoadingTableBody = (
    <TableBody>
      <TableRow>
        <TableCell colSpan={listOfLabelsForFiles.length} align={'center'}>
          <Typography>Loading...</Typography>
        </TableCell>
      </TableRow>
    </TableBody>
  );

  const renderErrorTableBody = (
    <TableBody>
      <TableRow>
        <TableCell colSpan={listOfLabelsForFiles.length} align={'center'}>
          <Typography>
            An error occurred while fetching contracts. Please try again later.
          </Typography>
        </TableCell>
      </TableRow>
    </TableBody>
  );

  const renderEmptyTableBody = (
    <TableBody>
      <TableRow>
        <TableCell colSpan={listOfLabelsForFiles.length} align={'center'}>
          <Typography>No contracts found.</Typography>
        </TableCell>
      </TableRow>
    </TableBody>
  );

  const renderTableBody = (
    <TableBody>
      {contractQuery?.data?.data?.map((contract) => (
        <TableRow
          key={contract._id}
          hover
          onClick={() => {
            setSelectedFile(contract);
          }}
          sx={{
            cursor: 'pointer',
          }}
        >
          <TableCell>{contract.file_name}</TableCell>
          <TableCell>{contract.contract_type}</TableCell>
          <TableCell>{contract.pages}</TableCell>
          {Object.entries(contract.properties).map(([key, value]) => (
            <TableCell key={key}>{value}</TableCell>
          ))}
        </TableRow>
      ))}
    </TableBody>
  );

  return (
    <Column>
      {renderHeader}

      {contractQuery.isLoading && <LoadingTopbar />}

      <Card variant="outlined">
        <TableContainer sx={{ overflow: 'unset' }}>
          <Scrollbar>
            <Table>
              <TableHeadCustom headLabel={listOfLabelsForFiles} />
              {contractQuery.isLoading
                ? renderLoadingTableBody
                : contractQuery.isError
                  ? renderErrorTableBody
                  : contractQuery?.data?.data?.length == 0
                    ? renderEmptyTableBody
                    : renderTableBody}
            </Table>
          </Scrollbar>
        </TableContainer>
      </Card>

      <Dialog
        open={!!selectedFile}
        onClose={() => {
          setSelectedFile(null);
        }}
        fullWidth
        maxWidth={'xl'}
      >
        <DialogContent sx={{ margin: 0.25 }}>
          <Box
            dangerouslySetInnerHTML={{ __html: selectedFile?.marked_html || '' }}
            sx={{
              padding: 2,
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setSelectedFile(null);
            }}
            color="primary"
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Column>
  );
};

export default ContractCompareView;
